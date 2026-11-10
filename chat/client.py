"""Minimal HTTP client for the text chat of the system under test (a reference contract: routes come from config/settings.py).

Flow: access key -> session cookie -> access token -> start scenario -> send turns.
The access key comes from CHATQA_ACCESS_KEY (set it in the git-ignored config/local.env, test keys only);
if it is missing it is asked on the terminal and not saved.
"""
import getpass
import http.cookiejar
import json
import time
import os
import ssl
import urllib.error
import urllib.request

from config.settings import ROUTE_SCENARIOS, ROUTE_SESSION, ROUTE_TOKEN


class ChatError(Exception):
    pass


def _redact(v):
    """Payload/response as shown in the report: secrets and big audio blobs are replaced by a short note."""
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            if k in ("token", "key"):
                out[k] = "<redacted>"
            elif k in ("audio_base64", "reply_audio_base64") and isinstance(x, str):
                out[k] = f"<{len(x)} base64 chars (audio)>"
            else:
                out[k] = _redact(x)
        return out
    if isinstance(v, list):
        return [_redact(x) for x in v]
    return v


def _pinned_context() -> ssl.SSLContext:
    """TLS context. Verification is always ON. If CHATQA_CA_FILE is set, that certificate (a private CA or the server's own
    pinned certificate) is trusted for this tool only; any other certificate is rejected."""
    from config.settings import CA_FILE
    ctx = ssl.create_default_context(cafile=str(CA_FILE)) if CA_FILE else ssl.create_default_context()
    ctx.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN  # the pinned file is the server's own (leaf) certificate
    return ctx


class ChatClient:
    def __init__(self, base_url: str, key: str | None = None):
        self.base = base_url.rstrip("/")
        self._key = key
        self._jar = http.cookiejar.CookieJar()
        handlers = [urllib.request.HTTPCookieProcessor(self._jar)]
        if self.base.startswith("https"):
            handlers.append(urllib.request.HTTPSHandler(context=_pinned_context()))
        self._http = urllib.request.build_opener(*handlers)
        self._token: str | None = None
        self.log: list = []  # redacted exchanges: {method, path, status, request, response}
        self.server_errors: list = []  # (path, status) of 5xx answers that were retried; shown in the report, never hidden

    def _call(self, path: str, body: dict | None = None, auth: bool = False, _retry: bool = False, _server: int = 0):
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = f"Bearer {self._token}"
        req = urllib.request.Request(self.base + path, method="POST", headers=headers,
                                     data=json.dumps(body if body is not None else {}).encode("utf-8"))
        try:
            with self._http.open(req, timeout=120) as r:
                raw = r.read().decode("utf-8")
                status, resp = r.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            status, resp, raw = e.code, {}, e.read().decode("utf-8", "replace")
        if status == 401 and auth and not _retry:  # the token expires (during the 1-minute gap between runs): log in again once
            self.login()
            return self._call(path, body, auth, _retry=True)
        if status in (500, 502, 503, 504) and auth and _server < 4:  # the test environment sometimes answers 5xx once: log it, wait, try again (four times at most)
            self.server_errors.append((path, status))
            self.log.append({"method": "POST", "url": self.base + path, "path": path, "status": status,
                             "request_raw": req.data.decode("utf-8"), "response_raw": raw,
                             "request_headers": ["Content-Type: application/json", "Authorization: Bearer <hidden>"]})
            time.sleep(5)
            return self._call(path, body, auth, _retry, _server + 1)
        if path not in (ROUTE_SESSION, ROUTE_TOKEN):  # login calls carry the key and the token: never logged
            # verbatim: the request body as sent and the response body as received (the Authorization header is the only thing hidden)
            self.log.append({"method": "POST", "url": self.base + path, "path": path, "status": status,
                             "request_raw": req.data.decode("utf-8"), "response_raw": raw,
                             "request_headers": ["Content-Type: application/json"] + (["Authorization: Bearer <hidden>"] if auth else [])})
        return status, resp

    def login(self) -> None:
        status, body = self._call(ROUTE_TOKEN)
        if status == 401:
            key = self._key or os.environ.get("CHATQA_ACCESS_KEY")
            s = self._call(ROUTE_SESSION, {"key": key.strip()})[0] if key else 401
            if s not in (200, 204):  # missing or rejected key (a local dev key is usually not the shared environment's): ask once, not saved
                key = getpass.getpass("Access key for this server (typed here, not saved): ")
                s = self._call(ROUTE_SESSION, {"key": key.strip()})[0]
                if s not in (200, 204):
                    raise ChatError(f"session failed with {s}")
            status, body = self._call(ROUTE_TOKEN)
        if status != 200 or "token" not in body:
            raise ChatError(f"token failed with {status}")
        self._token = body["token"]

    def start(self) -> dict:
        status, body = self._call(ROUTE_SCENARIOS, {}, auth=True)
        if status != 201:
            raise ChatError(f"start scenario failed with {status}")
        return body

    def say(self, scenario_id: str, turn_index: int, text: str) -> dict:
        status, body = self._call(f"{ROUTE_SCENARIOS}/{scenario_id}/turns",
                                  {"turn": turn_index, "text": text}, auth=True)
        if status != 200:
            raise ChatError(f"turn {turn_index} failed with {status}")
        return body
