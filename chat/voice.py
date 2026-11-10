"""English speech for the voice scenarios: text -> edge-tts (MP3) -> 16 kHz mono PCM16 WAV, the format the chat page records.

Needs internet (edge-tts talks to Microsoft's TTS service) and the packages from requirements.txt.
Only synthetic canary sentences are ever sent there; never real child data.
"""
import asyncio
import io
import wave

VOICE = "en-US-AnaNeural"  # a child-like English neural voice
SAMPLE_RATE = 16_000  # same as CAPTURE_SAMPLE_RATE_HZ in the frontend's useBatchVoice


class VoiceUnavailable(Exception):
    """Speech could not be produced (no internet, packages missing)."""


def speak_wav(text: str, voice: str = VOICE) -> bytes:
    try:
        import edge_tts
        import miniaudio
    except ImportError as e:
        raise VoiceUnavailable(f"package missing: {e.name}; run: pip install -r requirements.txt inside the project venv") from e

    async def synth() -> bytes:
        data = b""
        async for chunk in edge_tts.Communicate(text, voice).stream():
            if chunk["type"] == "audio":
                data += chunk["data"]
        return data

    try:
        mp3 = asyncio.run(synth())
    except Exception as e:
        raise VoiceUnavailable(f"edge-tts failed: {type(e).__name__}: {e}") from e
    if not mp3:
        raise VoiceUnavailable("edge-tts returned no audio")
    pcm = miniaudio.decode(mp3, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=SAMPLE_RATE)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.samples.tobytes())
    return buf.getvalue()
