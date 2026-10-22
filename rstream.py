#!/usr/bin/env python3
"""
discord streaming badge spoofer - inflate the "streamed to others" hours.

SahrulRD-Smatel, 2026. mit licensed (see LICENSE).

posts stream_start and stream_end events to /api/v9/science, the same
endpoint the real client uses to credit streaming hours. duration_ms in
stream_end is accepted as-is by the server.

run:
    python rstream.py

shares the same science_state.json as rdiscord.py (token, cookie, fingerprint).
auth bits are identical — see rdiscord.py header for details.

this breaks discord tos. your account, your problem.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, Sequence

# paths — same state file as rdiscord.py so auth is shared
ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "science_state.json"

ME_URL = "https://discord.com/api/v9/users/@me?with_analytics_token=true"
SCIENCE_URL = "https://discord.com/api/v9/science"
PROPERTIES_URL = "https://cordapi.dolfi.es/api/v2/properties/windows"

BATCH_SIZE = 20           # stream sessions per /science request (keep lower than game spoofer)
BATCH_DELAY = 0.5         # seconds between requests
AUTH_MAX_AGE = 12 * 3600  # refetch the analytics token once the cache is older than this
DEBUG = False

# client identity — must stay in sync with rdiscord.py
CLIENT_VERSION = "1.0.9253"
CLIENT_BUILD_NUMBER = 594031
NATIVE_BUILD_NUMBER = 88414
OS_VERSION = "10.0.26200"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) discord/1.0.9253 Chrome/148.0.7778.280 "
    "Electron/42.7.1 Safari/537.36"
)


def _user_id_from_token(token: str) -> str:
    try:
        first = token.split(".", 1)[0]
        pad = "=" * (-len(first) % 4)
        return base64.b64decode(first + pad).decode("utf-8")
    except Exception:
        return ""


# ── DPAPI encryption (Windows) ──────────────────────────────────────────────
# identical to rdiscord.py — ties saved credentials to YOUR Windows user.

_DPAPI_PREFIX = "dpapi:"
_SENSITIVE_FIELDS = ("token", "cookie", "fingerprint", "analytics_token")


def _dpapi_encrypt(plaintext: str) -> str:
    if not plaintext or os.name != "nt" or plaintext.startswith(_DPAPI_PREFIX):
        return plaintext
    import ctypes
    import ctypes.wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD),
                     ("pbData", ctypes.POINTER(ctypes.c_char))]

    raw = plaintext.encode("utf-8")
    inp = _Blob(len(raw), ctypes.create_string_buffer(raw, len(raw)))
    out = _Blob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(inp), None, None, None, None, 0, ctypes.byref(out)
    ):
        return plaintext
    encrypted = ctypes.string_at(out.pbData, out.cbData)
    ctypes.windll.kernel32.LocalFree(out.pbData)
    return _DPAPI_PREFIX + base64.b64encode(encrypted).decode("ascii")


def _dpapi_decrypt(ciphertext: str) -> str:
    if not ciphertext or os.name != "nt" or not ciphertext.startswith(_DPAPI_PREFIX):
        return ciphertext
    import ctypes
    import ctypes.wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD),
                     ("pbData", ctypes.POINTER(ctypes.c_char))]

    raw = base64.b64decode(ciphertext[len(_DPAPI_PREFIX):])
    inp = _Blob(len(raw), ctypes.create_string_buffer(raw, len(raw)))
    out = _Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(inp), None, None, None, None, 0, ctypes.byref(out)
    ):
        return ciphertext
    decrypted = ctypes.string_at(out.pbData, out.cbData)
    ctypes.windll.kernel32.LocalFree(out.pbData)
    return decrypted.decode("utf-8")


# ── Console ──────────────────────────────────────────────────────────────────

class Console:
    """colored console output — themed for streaming."""

    RED = "\x1b[91m"
    PURPLE = "\x1b[38;5;141m"    # streaming accent (purple like Go Live)
    GREEN = "\x1b[92m"
    YELLOW = "\x1b[93m"
    WHITE = "\x1b[97m"
    GREY = "\x1b[90m"
    CYAN = "\x1b[96m"
    RESET = "\x1b[0m"
    RULE = "─" * 44

    def __init__(self) -> None:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        if sys.platform == "win32":
            self._enable_ansi()

    @staticmethod
    def _enable_ansi() -> None:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)

    def _stamp(self) -> str:
        return f"{self.GREY}{time.strftime('%H:%M:%S')}{self.RESET}"

    def _line(self, glyph: str, target: str, detail: str, color: str) -> None:
        print(f"  {self._stamp()} {glyph} {self.WHITE}{target}{self.RESET} "
              f"{self.GREY}·{self.RESET} {color}{detail}{self.RESET}")

    def ok(self, target: str, detail: str) -> None:
        self._line(f"{self.GREEN}✓{self.RESET}", target, detail, self.GREEN)

    def sent(self, target: str, detail: str) -> None:
        self._line(f"{self.GREY}·{self.RESET} {self.GREEN}sent{self.RESET}", target, detail, self.GREEN)

    def warn(self, target: str, detail: str) -> None:
        self._line(f"{self.YELLOW}!{self.RESET}", target, detail, self.YELLOW)

    def err(self, target: str, detail: str) -> None:
        self._line(f"{self.RED}✗{self.RESET}", target, detail, self.RED)

    def info(self, detail: str) -> None:
        print(f"  {self._stamp()} {self.GREY}·{self.RESET} {self.WHITE}{detail}{self.RESET}")

    def rule(self) -> None:
        print(f"  {self.GREY}{self.RULE}{self.RESET}")

    def clear(self) -> None:
        print("\x1b[2J\x1b[3J\x1b[H", end="")

    def banner(self) -> None:
        self.clear()
        print()
        print(f"  {self.PURPLE}spoofer{self.RESET} {self.GREY}·{self.RESET} {self.WHITE}streaming badge{self.RESET}")
        print(f"    {self.GREY}by SahrulRD-Smatel{self.RESET}")
        print()


# ── State ────────────────────────────────────────────────────────────────────

@dataclass
class State:
    """persisted auth: shared with rdiscord.py's science_state.json."""

    token: str = ""
    cookie: str = ""
    fingerprint: str = ""
    analytics_token: str = ""
    fetched_at: int = 0
    # game-spoofer fields — kept so we don't clobber them when saving
    used_games: list[str] = None
    total_games_claimed: int = 0
    total_hours_claimed: float = 0.0
    # streaming-specific stats
    total_stream_sessions: int = 0
    total_stream_hours: float = 0.0

    def __post_init__(self) -> None:
        if self.used_games is None:
            self.used_games = []

    @classmethod
    def load(cls) -> "State":
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            # build state from known fields, ignoring unknowns
            known = cls().__dict__
            state = cls(**{k: data.get(k, v) for k, v in known.items() if k != "used_games"})
            state.used_games = data.get("used_games", [])
            for field in _SENSITIVE_FIELDS:
                val = getattr(state, field, "")
                if val:
                    setattr(state, field, _dpapi_decrypt(val))
            return state
        return cls()

    def save(self) -> None:
        # preserve any extra keys rdiscord.py may have written
        existing: dict = {}
        if STATE_FILE.exists():
            try:
                existing = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        data = {**existing, **asdict(self)}
        for field in _SENSITIVE_FIELDS:
            if field in data and data[field]:
                data[field] = _dpapi_encrypt(data[field])
        STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @property
    def is_stale(self) -> bool:
        return not self.analytics_token or (time.time() - self.fetched_at) > AUTH_MAX_AGE

    @property
    def has_cookie(self) -> bool:
        return bool(self.cookie.strip())

    @property
    def has_token(self) -> bool:
        return bool(self.token.strip())


# ── Auth helpers ─────────────────────────────────────────────────────────────

def _local_props() -> dict:
    return {
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": CLIENT_VERSION,
        "os_version": OS_VERSION,
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-GB",
        "has_client_mods": False,
        "browser_user_agent": USER_AGENT,
        "browser_version": "42.7.1",
        "os_sdk_version": "26200",
        "client_build_number": CLIENT_BUILD_NUMBER,
        "native_build_number": NATIVE_BUILD_NUMBER,
        "client_event_source": None,
        "client_app_state": "focused",
    }


def build_super_props(launch_signature: str, heartbeat_session: str) -> str:
    try:
        req = urllib.request.Request(PROPERTIES_URL, method="POST", data=b"{}",
                                     headers={"content-type": "application/json", "user-agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as response:
            props = json.loads(response.read().decode("utf-8"))["properties"]
    except Exception:
        props = _local_props()
    props["client_launch_id"] = str(uuid.uuid4())
    props["launch_signature"] = launch_signature
    props["client_heartbeat_session_id"] = heartbeat_session
    raw = json.dumps(props, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _read_analytics_token(auth_token: str, super_props: str) -> str:
    req = urllib.request.Request(ME_URL, headers={
        "authorization": auth_token,
        "user-agent": USER_AGENT,
        "x-super-properties": super_props,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"token rejected ({exc.code})") from exc
    token = data.get("analytics_token")
    if not token:
        raise RuntimeError("no analytics_token in response")
    return token


def ensure_token(state: State, super_props: str) -> None:
    if not state.is_stale:
        return
    state.analytics_token = _read_analytics_token(state.token, super_props)
    state.fetched_at = int(time.time())
    state.save()


@dataclass(frozen=True)
class Session:
    """per-run client identity."""
    heartbeat_session: str
    launch_signature: str
    super_props: str

    @classmethod
    def new(cls) -> "Session":
        hb = str(uuid.uuid4())
        sig = str(uuid.uuid4())
        return cls(hb, sig, build_super_props(sig, hb))


# ── Streaming events ─────────────────────────────────────────────────────────
# Discord tracks streaming hours via stream_start + stream_end events posted
# to /api/v9/science. The key fields:
#   - guild_id / channel_id:  where the stream happened
#   - stream_key:             "guild:<guild_id>:<channel_id>:<user_id>"
#   - rtc_connection_id:      ties to a voice connection
#   - media_session_id:       ties to a media session
#   - duration_ms (stream_end): total streaming duration

# fake guilds/channels to stream "from" — uses realistic-looking snowflakes
# these don't need to be real; science telemetry is write-only and doesn't
# validate guild membership for event ingestion.
_FAKE_GUILDS = [
    {"guild_id": "1095834721568923648", "channel_id": "1095834721568923651"},
    {"guild_id": "1147892345678901234", "channel_id": "1147892345678901237"},
    {"guild_id": "1203456789012345678", "channel_id": "1203456789012345681"},
    {"guild_id": "1156789012345678901", "channel_id": "1156789012345678904"},
    {"guild_id": "1178901234567890123", "channel_id": "1178901234567890126"},
    {"guild_id": "1189012345678901234", "channel_id": "1189012345678901237"},
    {"guild_id": "1190123456789012345", "channel_id": "1190123456789012348"},
    {"guild_id": "1201234567890123456", "channel_id": "1201234567890123459"},
]


class StreamClient:
    """builds and posts stream_start / stream_end events."""

    def __init__(self, state: State, session: Session) -> None:
        self.state = state
        self.session = session
        self._seq = 0
        self._user_id = _user_id_from_token(state.token)

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _pick_guild(self, index: int) -> dict:
        return _FAKE_GUILDS[index % len(_FAKE_GUILDS)]

    def build_stream_session(self, duration_ms: int, index: int = 0) -> list[dict]:
        """build a complete stream_start + stream_end pair for one session."""
        guild = self._pick_guild(index)
        guild_id = guild["guild_id"]
        channel_id = guild["channel_id"]
        stream_key = f"guild:{guild_id}:{channel_id}:{self._user_id}"
        rtc_connection_id = str(uuid.uuid4())
        media_session_id = uuid.uuid4().hex

        now = int(time.time() * 1000)
        start_ts = now - duration_ms
        if start_ts < 0:
            start_ts = now

        start_event = {
            "type": "stream_start",
            "properties": {
                "client_track_timestamp": start_ts,
                "client_heartbeat_session_id": self.session.heartbeat_session,
                "event_sequence_number": self._next_seq(),
                "guild_id": guild_id,
                "channel_id": channel_id,
                "stream_key": stream_key,
                "rtc_connection_id": rtc_connection_id,
                "media_session_id": media_session_id,
                "source_type": "desktop",
                "application_id": None,
                "quality_options": {
                    "resolution": 1080,
                    "fps": 60,
                },
                "rtc_server_id": uuid.uuid4().hex[:12],
                "parent_app_id": None,
                "streamer_delay": 0,
                "viewers_count": 1,
                "launch_signature": self.session.launch_signature,
                "client_app_state": "focused",
                "client_send_timestamp": start_ts,
            },
        }

        end_event = {
            "type": "stream_end",
            "properties": {
                "client_track_timestamp": now,
                "client_heartbeat_session_id": self.session.heartbeat_session,
                "event_sequence_number": self._next_seq(),
                "guild_id": guild_id,
                "channel_id": channel_id,
                "stream_key": stream_key,
                "rtc_connection_id": rtc_connection_id,
                "media_session_id": media_session_id,
                "duration_ms": duration_ms,
                "source_type": "desktop",
                "finish_reason": "normal",
                "viewers_count": 1,
                "average_viewers": 1,
                "max_viewers": 1,
                "quality_options": {
                    "resolution": 1080,
                    "fps": 60,
                },
                "launch_signature": self.session.launch_signature,
                "client_app_state": "focused",
                "client_send_timestamp": now,
            },
        }

        return [start_event, end_event]

    def post(self, events: Sequence[dict]) -> int:
        """post a batch. returns the http status (204 = accepted)."""
        payload = {"token": self.state.analytics_token, "events": list(events)}
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB",
            "authorization": self.state.token,
            "content-type": "application/json",
            "cookie": self.state.cookie,
            "origin": "https://discord.com",
            "referer": "https://discord.com/channels/@me",
            "user-agent": USER_AGENT,
            "x-debug-options": "bugReporterEnabled",
            "x-discord-locale": "en-GB",
            "x-discord-timezone": "Europe/Oslo",
            "x-super-properties": self.session.super_props,
        }
        if DEBUG:
            print("\n" + "=" * 72)
            print(f"POST {SCIENCE_URL} ({len(payload['events'])} events)")
            print("headers:", json.dumps(headers, indent=2))
            print("body:", json.dumps(payload, indent=2))
            print("=" * 72)
        request = urllib.request.Request(SCIENCE_URL, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except Exception as exc:
            if DEBUG:
                import traceback
                traceback.print_exc()
            else:
                print(f"  \x1b[91m  network error: {exc}\x1b[0m")
            return 0


# ── Spoofer ──────────────────────────────────────────────────────────────────

class StreamSpoofer:
    """sends stream sessions in batches and logs progress."""

    def __init__(self, client: StreamClient, console: Console) -> None:
        self.client = client
        self.console = console

    def run(self, count: int, duration_ms: int) -> int:
        """send `count` fake stream sessions. returns number of sessions accepted."""
        sent_ok = 0
        batch_num = 0
        for start in range(0, count, BATCH_SIZE):
            batch_num += 1
            end = min(start + BATCH_SIZE, count)
            events: list[dict] = []
            for i in range(start, end):
                events.extend(self.client.build_stream_session(duration_ms, index=i))

            # retry up to 3 times on transient failures
            status = 0
            for attempt in range(3):
                status = self.client.post(events)
                if status in (204, 401, 403):
                    break
                if attempt < 2:
                    delay = BATCH_DELAY * (attempt + 2)
                    self.console.warn(f"batch {batch_num}", f"[{status}] retrying in {delay:.1f}s...")
                    time.sleep(delay)

            sessions_in_batch = end - start
            if status == 204:
                sent_ok += sessions_in_batch
                self.console.sent(f"batch {batch_num}", f"{sent_ok}/{count} sessions")
            elif status in (401, 403):
                self.console.err(f"batch {batch_num}",
                                 f"[{status}] auth rejected · refresh (option 2) with a fresh cookie")
                return sent_ok
            else:
                self.console.warn(f"batch {batch_num}", f"[{status}] failed after 3 attempts")
            time.sleep(BATCH_DELAY)
        return sent_ok


# ── App ──────────────────────────────────────────────────────────────────────

# streaming badge tiers for reference display
STREAM_TIERS = [
    (1, "Newcomer"),
    (5, "Fledgling"),
    (20, "Breakout"),
    (75, "Standout"),
    (150, "Trendsetter"),
    (300, "Headliner"),
    (500, "Star"),
    (1000, "Sensation"),
    (2000, "Visionary"),
    (5000, "Phenomenon"),
]


def _current_tier(hours: float) -> str:
    tier = "None"
    for threshold, name in STREAM_TIERS:
        if hours >= threshold:
            tier = name
        else:
            break
    return tier


def _next_tier(hours: float) -> str:
    for threshold, name in STREAM_TIERS:
        if hours < threshold:
            return f"{name} ({threshold}h)"
    return "MAX (Phenomenon)"


class App:
    def __init__(self) -> None:
        self.console = Console()
        self.state = State.load()
        self.session: Session | None = None
        self.client: StreamClient | None = None

    # startup

    def start(self) -> None:
        self.console.banner()
        time.sleep(0.8)
        print()

        C = self.console

        # step 1: token
        if not self.state.has_token:
            self._prompt_token()
        else:
            C.ok("auth", "token loaded")
            time.sleep(0.5)
        if not self.state.has_token:
            C.err("token", "required to run")
            return

        # step 2: cookie
        if not self.state.has_cookie:
            self.console.banner()
            self._prompt_cookie()
        else:
            C.ok("auth", "cookie loaded")
            time.sleep(0.5)
        if not self.state.has_cookie:
            C.err("cookie", "required to run")
            return

        # step 3: auth
        self.console.banner()
        print()
        C.info("validating auth...")
        self._new_session()
        try:
            ensure_token(self.state, self.session.super_props)
        except Exception as exc:
            C.err("token", str(exc))
            return
        C.ok("auth", "ready")
        time.sleep(0.5)

        print()
        self.menu()

    def _new_session(self) -> None:
        self.session = Session.new()
        self.client = StreamClient(self.state, self.session)

    # auth

    def _prompt_token(self) -> None:
        self.console.info("paste your discord account token")
        entered = input(f"  {self.console.GREY}token:{self.console.RESET} ").strip()
        if entered:
            self.state.token = entered
            self.state.save()
            self.console.ok("token", "saved")
            time.sleep(1.5)

    def _prompt_cookie(self) -> None:
        self.console.info("paste your cf_clearance cookie header")
        entered = input(f"  {self.console.GREY}cookie:{self.console.RESET} ").strip()
        if entered:
            self.state.cookie = entered
            self.state.save()
            self.console.ok("cookie", "saved")
            time.sleep(1.5)

    def _refresh(self) -> None:
        self.console.info("update cookie? [y/n]")
        choice = input(f"  {self.console.GREY}›{self.console.RESET} ").strip().lower()
        if choice in ("y", "yes"):
            self.console.info("paste a fresh cookie header")
            entered = input(f"  {self.console.GREY}cookie:{self.console.RESET} ").strip()
            if entered:
                self.state.cookie = entered
                self.console.ok("cookie", "updated")
            else:
                self.console.info("cookie unchanged")

        self.console.info("refreshing analytics token...")
        try:
            self.state.fetched_at = 0
            ensure_token(self.state, self.session.super_props)
        except Exception as exc:
            self.console.err("auth", str(exc))
            return
        self._new_session()
        self.state.save()
        self.console.ok("auth", "refreshed")
        time.sleep(1.5)

    def _require_ready(self) -> bool:
        if not self.state.has_cookie:
            self.console.err("cookie", "not set · use option 2 to refresh")
            return False
        if self.state.is_stale:
            try:
                ensure_token(self.state, self.session.super_props)
            except Exception as exc:
                self.console.err("auth", str(exc))
                return False
            self._new_session()
        return bool(self.state.analytics_token)

    # modules

    def claim_streaming(self) -> None:
        """claim streaming hours."""
        if not self._require_ready():
            return
        C = self.console

        # show tier info
        print()
        current = _current_tier(self.state.total_stream_hours)
        next_up = _next_tier(self.state.total_stream_hours)
        C.info(f"current tier: {C.PURPLE}{current}{C.WHITE}")
        C.info(f"next tier: {C.CYAN}{next_up}{C.WHITE}")
        C.info(f"total claimed: {C.PURPLE}{self.state.total_stream_hours:,.0f}h{C.WHITE}")
        C.rule()

        # prompt for sessions
        raw_count = input(f"  {C.GREY}how many stream sessions? [50]:{C.RESET} ").strip()
        try:
            count = int(raw_count) if raw_count else 50
        except ValueError:
            C.err("input", "invalid count")
            return
        if count <= 0:
            C.err("input", "count must be positive")
            return

        # prompt for hours per session
        raw_hours = input(f"  {C.GREY}hours per session? [1]:{C.RESET} ").strip()
        try:
            hours = float(raw_hours) if raw_hours else 1.0
        except ValueError:
            C.err("input", "invalid hours")
            return
        if hours <= 0:
            C.err("input", "hours must be positive")
            return

        duration_ms = int(hours * 3600 * 1000)
        total_hours = count * hours
        print()
        C.info(
            f"claiming {C.PURPLE}{hours:g}h{C.WHITE} on "
            f"{C.PURPLE}{count}{C.WHITE} sessions "
            f"{C.GREY}·{C.WHITE} {total_hours:,.0f}h total"
        )
        C.rule()

        ok = StreamSpoofer(self.client, self.console).run(count, duration_ms)
        print()
        C.ok("complete", f"{ok}/{count} sessions · {ok * hours:,.0f}h claimed")

        # accumulate stats
        self.state.total_stream_sessions += ok
        self.state.total_stream_hours += ok * hours
        self.state.save()

        # show updated tier
        new_tier = _current_tier(self.state.total_stream_hours)
        if new_tier != current:
            print()
            C.ok("tier up!", f"{C.PURPLE}{new_tier}{C.RESET}")

        C.rule()
        input(f"  {C.PURPLE}›{C.RESET} press enter to continue")
        C.rule()

    def show_tiers(self) -> None:
        """display the streaming badge tiers."""
        C = self.console
        print()
        C.info(f"{C.PURPLE}streaming badge tiers{C.WHITE}")
        C.rule()
        for threshold, name in STREAM_TIERS:
            marker = f" {C.GREEN}◀ you are here{C.RESET}" if (
                self.state.total_stream_hours >= threshold and
                (threshold == STREAM_TIERS[-1][0] or self.state.total_stream_hours < STREAM_TIERS[STREAM_TIERS.index((threshold, name)) + 1][0])
            ) else ""
            C.info(f"  {C.PURPLE}{threshold:>5,}h{C.WHITE} · {name}{marker}")
        C.rule()
        input(f"  {C.PURPLE}›{C.RESET} press enter to continue")

    # menu

    def menu(self) -> None:
        C = self.console
        while True:
            C.clear()
            C.banner()
            print()
            # show stats
            current = _current_tier(self.state.total_stream_hours)
            C.info(f"tier: {C.PURPLE}{current}{C.WHITE} · {C.PURPLE}{self.state.total_stream_hours:,.0f}h{C.WHITE} streamed")
            C.info(f"sessions: {C.PURPLE}{self.state.total_stream_sessions}{C.WHITE}")
            C.rule()
            C.info(f"{C.PURPLE}1{C.RESET} · claim streaming hours")
            C.info(f"{C.PURPLE}2{C.RESET} · refresh auth")
            C.info(f"{C.PURPLE}3{C.RESET} · view badge tiers")
            C.info(f"{C.PURPLE}4{C.RESET} · exit")
            C.rule()
            choice = input(f"  {C.PURPLE}›{C.RESET} ").strip()
            print()
            if choice == "1":
                self.claim_streaming()
            elif choice == "2":
                self._refresh()
            elif choice == "3":
                self.show_tiers()
            elif choice in ("4", ""):
                break
            else:
                C.warn("input", "invalid option")


def main() -> None:
    try:
        App().start()
    except KeyboardInterrupt:
        print()
        Console().warn("exit", "interrupted")


if __name__ == "__main__":
    main()
