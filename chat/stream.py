"""Streaming voice: one WebSocket for the whole conversation, the way a web client talks to the voice assistant.

The service relays a live model session, so the model keeps the context between turns. The client sends an empty `setup` frame, the
assistant opens the conversation by itself, then each child turn is audio (PCM16 16 kHz mono) followed by a little silence; the reply is
read from the output transcription until `turnComplete` (a Live-API-style frame layout; adapt `_read_turn` to your service). Audio frames
are kept out of the logged text (their size is noted) so the report stays readable; everything else is logged as received.
"""
import asyncio
import json
import time
import re

from chat.client import ChatClient, ChatError, _pinned_context
from config.settings import ROUTE_STREAM as ROUTE

CHUNK = 3200  # 100 ms of PCM16 at 16 kHz
SILENCE_SECONDS = 1.5
TURN_TIMEOUT = 60


def _pcm(wav: bytes) -> bytes:
    """The PCM payload of a WAV file written by chat.voice (44-byte header, PCM16 16 kHz mono)."""
    i = wav.find(b"data")
    return wav[i + 8:] if i >= 0 else wav


def _short(frame: str) -> str:
    """A received frame as text; the base64 audio is replaced by its size."""
    return re.sub(r'("data":\s*")([A-Za-z0-9+/=]{200,})(")', lambda m: f'{m.group(1)}[audio base64, {len(m.group(2))} chars]{m.group(3)}', frame)


class VoiceStream:
    def __init__(self, chat: ChatClient):
        self.chat = chat
        self.url = chat.base.replace("https://", "wss://").replace("http://", "ws://") + ROUTE
        self.loop = asyncio.new_event_loop()
        self.ws = None
        self.turns = 0

    def _run(self, coro):
        return self.loop.run_until_complete(coro)

    def open(self) -> str:
        """Connect, send the setup and read the assistant's opening line (it speaks first). Returns the opening text."""
        import websockets
        cookie = "; ".join(f"{c.name}={c.value}" for c in self.chat._jar)
        ssl_ctx = _pinned_context() if self.url.startswith("wss") else None

        async def go():
            self.ws = await websockets.connect(self.url, ssl=ssl_ctx, additional_headers={"Cookie": cookie}, max_size=None,
                                               ping_interval=None)  # our loop only runs during a turn, so it cannot answer pings in between
            await self.ws.send(json.dumps({"setup": {"realtimeInputConfig": {}}}))
            return await self._read_turn()

        last = None
        for attempt in range(3):  # the test environment sometimes drops the first connection; every drop is kept in the report
            try:
                reply, _, _ = self._run(go())
                return reply
            except Exception as e:
                last = e
                self.chat.server_errors.append((ROUTE, f"{type(e).__name__}: {e}"))
                if self.ws is not None:
                    try:
                        self._run(self.ws.close())
                    except Exception:
                        pass
                    self.ws = None
                time.sleep(5)
        raise ChatError(f"stream open failed 3 times: {type(last).__name__}: {last}") from last

    async def _read_turn(self) -> tuple:
        """Frames until turnComplete: (reply text, heard text, received frames)."""
        reply, heard, frames = [], [], []
        while True:
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=TURN_TIMEOUT)
            except asyncio.TimeoutError:
                raise ChatError(f"no turnComplete within {TURN_TIMEOUT}s (turn {self.turns + 1}, {len(frames)} frames received)")
            text = raw if isinstance(raw, str) else raw.decode("utf-8", "replace")
            frames.append(_short(text))
            try:
                data = json.loads(text)
            except ValueError:
                continue
            content = data.get("serverContent") or {}
            reply.append((content.get("outputTranscription") or {}).get("text", ""))
            heard.append((content.get("inputTranscription") or {}).get("text", ""))
            if content.get("turnComplete"):
                return "".join(reply).strip(), "".join(heard).strip(), frames

    def say(self, wav: bytes) -> dict:
        """Send one child turn (a WAV clip) and return {replyText, heardText} plus the log entry."""
        pcm = _pcm(wav) + b"\x00" * int(16000 * 2 * SILENCE_SECONDS)

        async def go():
            sent = 0
            for i in range(0, len(pcm), CHUNK):
                part = pcm[i:i + CHUNK]
                await self.ws.send(json.dumps({"realtimeInput": {"audio": {
                    "data": __import__("base64").b64encode(part).decode(), "mimeType": "audio/pcm;rate=16000"}}}))
                sent += len(part)
                await asyncio.sleep(0.02)
            return sent, await self._read_turn()

        try:
            sent, (reply, heard, frames) = self._run(go())
        except ChatError:
            raise
        except Exception as e:
            raise ChatError(f"stream turn {self.turns + 1} failed: {type(e).__name__}: {e}; close code={getattr(self.ws, 'close_code', None)} "
                            f"reason={getattr(self.ws, 'close_reason', None)}") from e
        self.turns += 1
        self.chat.log.append({
            "method": "WS", "url": self.url, "path": ROUTE, "status": 101,
            "request_raw": f"{sent} bytes of PCM16 16 kHz mono sent as {(sent + CHUNK - 1) // CHUNK} realtimeInput.audio frames "
                           f"(audio/pcm;rate=16000), the last {SILENCE_SECONDS} s are silence",
            "response_raw": "\n".join(frames) + f"\n--- heard (inputTranscription): {heard}\n--- reply (outputTranscription): {reply}",
            "request_headers": ["Cookie: <session, hidden>"]})
        return {"reply": reply, "heard": heard}

    def close(self) -> None:
        if self.ws is not None:
            try:
                self._run(self.ws.close())
            except Exception:
                pass
        self.loop.close()
