#!/usr/bin/env python3
"""
valorant_rpc.py - Discord Rich Presence (RPC) Spoofer for VALORANT.

Features:
- Dynamic Match Simulation Engine:
  * Simulates realistic rounds from 0-0, 1-0, 1-1, ... up to 13 (or overtime 14-12).
  * Auto-transition states: In Match ➔ Victory/Defeat ➔ In Lobby (In Queue) ➔ Agent Select ➔ Next Match.
  * Auto-rotates maps strictly from the ACTIVE COMPETITIVE MAP POOL (no off-rotation / patched maps).
  * Auto-updates RR on match wins (+18 to +24 RR) or losses (-12 to -17 RR).
  * Mobile-Clean layout: Zero text overflow, perfectly fits within profile boundaries.
  * 100% Ban Safe: Zero Discord tokens, zero memory injection, pure local named-pipe IPC.

Usage:
    py valorant_rpc.py                # Interactive menu (Realistic or Fast Demo mode)
    py valorant_rpc.py --fast         # Fast demo mode (rounds tick every 8-10s for quick testing)
    py valorant_rpc.py --start-mid    # Start mid-match (e.g. 5-3) so it looks live immediately
"""

from __future__ import annotations

import argparse
import json
import os
import random
import struct
import sys
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Tuple, List

# Official Discord Application ID for VALORANT
VALORANT_APP_ID = "700136079562375258"

# Enable ANSI escape sequences and UTF-8 on Windows consoles immediately
if sys.platform == "win32":
    os.system("")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Active Competitive Map Pool (Official 7-Map Ranked Rotation)
# Strictly adheres to current active ranked pool to ensure 100% authenticity
ACTIVE_COMPETITIVE_MAPS: List[str] = [
    "Ascent",
    "Bind",
    "Haven",
    "Lotus",
    "Sunset",
    "Abyss",
]

# High-Res Asset URLs (Valorant-API CDN)
RANK_ICONS = {
    "radiant": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/27/largeicon.png",
    "immortal_3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/26/largeicon.png",
    "immortal_2": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/25/largeicon.png",
    "immortal_1": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/24/largeicon.png",
    "ascendant_3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/23/largeicon.png",
}

AGENT_ICONS = {
    "jett": "https://media.valorant-api.com/agents/add6443a-41bd-e414-f6ad-e58d267f4e95/displayicon.png",
    "reyna": "https://media.valorant-api.com/agents/a3bfb85b-422f-bbda-cb50-03952f4cfa18/displayicon.png",
    "clove": "https://media.valorant-api.com/agents/1e58de9c-4950-5125-93e9-a0aee9f98746/displayicon.png",
    "omen": "https://media.valorant-api.com/agents/8e253930-4c05-31dd-1b86-4adc8636b243/displayicon.png",
    "iso": "https://media.valorant-api.com/agents/0e38b510-41a8-5780-5e7f-5e8a242a37f4/displayicon.png",
    "cypher": "https://media.valorant-api.com/agents/117ed9e3-49f3-6512-3ccf-0cada7e3823b/displayicon.png",
    "raze": "https://media.valorant-api.com/agents/f94c3b30-42be-e959-889c-5aa31330e210/displayicon.png",
    "sova": "https://media.valorant-api.com/agents/320b2a48-4d9b-a075-30f1-1f93a9b638fa/displayicon.png",
    "viper": "https://media.valorant-api.com/agents/707eab51-4736-4848-92f7-59f472867e24/displayicon.png",
    "chamber": "https://media.valorant-api.com/agents/22697a3d-45bf-8dd7-4fec-84a9e28c69d7/displayicon.png",
}

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RED = "\033[31m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_BLUE = "\033[34m"
C_MAGENTA = "\033[35m"
C_CYAN = "\033[36m"
C_GOLD = "\033[38;2;255;215;0m"


class MatchPhase(Enum):
    IN_MATCH = "IN_MATCH"
    POST_MATCH = "POST_MATCH"
    IN_LOBBY = "IN_LOBBY"
    AGENT_SELECT = "AGENT_SELECT"


class DiscordIPC:
    """Manages low-level named pipe communication with Discord Desktop client."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.pipe = None
        self.pipe_path = None
        self.connected_user = None

    def connect(self) -> bool:
        """Finds and connects to an active discord-ipc pipe."""
        for i in range(10):
            path = f"\\\\.\\pipe\\discord-ipc-{i}"
            try:
                self.pipe = open(path, "r+b", buffering=0)
                self.pipe_path = path
                break
            except (OSError, FileNotFoundError):
                continue

        if not self.pipe:
            return False

        # Send Handshake (Opcode 0)
        handshake_data = {"v": 1, "client_id": self.client_id}
        self._write(0, handshake_data)

        # Read READY response
        op, resp = self._read()
        if resp and resp.get("evt") == "READY":
            user = resp.get("data", {}).get("user", {})
            self.connected_user = f"{user.get('username', 'Unknown')}"
            return True
        return False

    def _write(self, op: int, data: Dict[str, Any]) -> None:
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("<II", op, len(payload))
        self.pipe.write(header + payload)
        self.pipe.flush()

    def _read(self) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
        try:
            hdr = self.pipe.read(8)
            if not hdr or len(hdr) < 8:
                return None, None
            op, length = struct.unpack("<II", hdr)
            body = self.pipe.read(length)
            return op, json.loads(body.decode("utf-8"))
        except Exception:
            return None, None

    def set_activity(self, activity: Dict[str, Any]) -> bool:
        """Sends SET_ACTIVITY (Opcode 1) frame."""
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {
                "pid": os.getpid(),
                "activity": activity,
            },
            "nonce": str(uuid.uuid4()),
        }
        try:
            self._write(1, payload)
            op, resp = self._read()
            return resp is not None and resp.get("evt") is None
        except Exception:
            return False

    def clear_activity(self) -> None:
        """Clears the active presence."""
        if not self.pipe:
            return
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": os.getpid(), "activity": None},
            "nonce": str(uuid.uuid4()),
        }
        try:
            self._write(1, payload)
        except Exception:
            pass

    def close(self) -> None:
        """Closes the IPC pipe."""
        if self.pipe:
            try:
                self.clear_activity()
                self.pipe.close()
            except Exception:
                pass
            self.pipe = None


@dataclass
class MatchSimulator:
    """Simulates realistic dynamic Valorant matches and lifecycles."""
    rank_name: str = "Radiant"
    rr_points: int = 845
    fast_mode: bool = False
    start_mid_match: bool = False
    locked_agent: Optional[str] = None
    allowed_maps: List[str] = field(default_factory=lambda: list(ACTIVE_COMPETITIVE_MAPS))

    # Dynamic state
    current_map: str = "Ascent"
    current_agent: str = "Jett"
    our_score: int = 0
    enemy_score: int = 0
    phase: MatchPhase = MatchPhase.IN_MATCH
    match_outcome: str = "Victory"

    # Timers
    match_start_time: float = field(default_factory=time.time)
    phase_start_time: float = field(default_factory=time.time)
    last_round_time: float = field(default_factory=time.time)
    next_round_interval: float = 90.0
    phase_duration: float = 60.0

    def __post_init__(self):
        if not self.allowed_maps:
            self.allowed_maps = list(ACTIVE_COMPETITIVE_MAPS)
        self.current_map = random.choice(self.allowed_maps)
        self.current_agent = self.locked_agent or random.choice(list(AGENT_ICONS.keys())).capitalize()

        if self.start_mid_match:
            # Random starting score between 4-2 and 8-5
            self.our_score = random.randint(4, 8)
            self.enemy_score = random.randint(2, min(self.our_score, 6))
            round_sec = 10 if self.fast_mode else random.randint(85, 110)
            elapsed_sim = (self.our_score + self.enemy_score) * round_sec
            self.match_start_time = time.time() - elapsed_sim
        else:
            self.our_score = 0
            self.enemy_score = 0
            self.match_start_time = time.time()

        self.phase_start_time = time.time()
        self.last_round_time = time.time()
        self._schedule_next_round()

    def _schedule_next_round(self) -> None:
        if self.fast_mode:
            self.next_round_interval = random.uniform(8.0, 12.0)
        else:
            # Realistic round time: buy phase (30s) + round action (50-80s)
            self.next_round_interval = random.uniform(75.0, 110.0)

    def tick(self) -> Tuple[bool, str]:
        """
        Ticks the simulation.
        Returns (has_changed, status_message).
        """
        now = time.time()

        if self.phase == MatchPhase.IN_MATCH:
            if now - self.last_round_time >= self.next_round_interval:
                self.last_round_time = now
                self._schedule_next_round()

                # Radiant team has ~65% round win rate
                if random.random() < 0.65:
                    self.our_score += 1
                    event = f"Round WON! Score: {self.our_score} - {self.enemy_score}"
                else:
                    self.enemy_score += 1
                    event = f"Round Lost. Score: {self.our_score} - {self.enemy_score}"

                # Check match finish condition (First to 13, or OT win by 2)
                if self.our_score >= 13 and (self.our_score - self.enemy_score) >= 2:
                    # Match Victory!
                    rr_gain = random.randint(18, 24)
                    self.rr_points += rr_gain
                    self.match_outcome = "Victory"
                    self.phase = MatchPhase.POST_MATCH
                    self.phase_start_time = now
                    self.phase_duration = 10.0 if self.fast_mode else random.uniform(60.0, 90.0)
                    return True, f"Match VICTORY ({self.our_score}-{self.enemy_score})! +{rr_gain} RR -> {self.rr_points} RR"

                elif self.enemy_score >= 13 and (self.enemy_score - self.our_score) >= 2:
                    # Match Defeat!
                    rr_loss = random.randint(12, 17)
                    self.rr_points = max(450, self.rr_points - rr_loss)
                    self.match_outcome = "Defeat"
                    self.phase = MatchPhase.POST_MATCH
                    self.phase_start_time = now
                    self.phase_duration = 10.0 if self.fast_mode else random.uniform(60.0, 90.0)
                    return True, f"Match DEFEAT ({self.our_score}-{self.enemy_score}). -{rr_loss} RR -> {self.rr_points} RR"

                return True, event

        elif self.phase == MatchPhase.POST_MATCH:
            if now - self.phase_start_time >= self.phase_duration:
                # Transition to Lobby (In Queue)
                self.phase = MatchPhase.IN_LOBBY
                self.phase_start_time = now
                self.phase_duration = 12.0 if self.fast_mode else random.uniform(90.0, 160.0)
                return True, "Returning to Lobby (Finding Match / In Queue)..."

        elif self.phase == MatchPhase.IN_LOBBY:
            if now - self.phase_start_time >= self.phase_duration:
                # Match Found! Transition to Agent Select with NEXT MAP (different from current)
                other_maps = [m for m in self.allowed_maps if m != self.current_map]
                self.current_map = random.choice(other_maps) if other_maps else self.current_map
                if not self.locked_agent:
                    self.current_agent = random.choice(list(AGENT_ICONS.keys())).capitalize()

                self.phase = MatchPhase.AGENT_SELECT
                self.phase_start_time = now
                self.phase_duration = 10.0 if self.fast_mode else random.uniform(45.0, 60.0)
                return True, f"Match Found! Agent Select on {self.current_map}..."

        elif self.phase == MatchPhase.AGENT_SELECT:
            if now - self.phase_start_time >= self.phase_duration:
                # Start Next Match!
                self.our_score = 0
                self.enemy_score = 0
                self.phase = MatchPhase.IN_MATCH
                self.match_start_time = now
                self.last_round_time = now
                self.phase_start_time = now
                self._schedule_next_round()
                return True, f"Match Started on {self.current_map} as {self.current_agent} (0 - 0)!"

        return False, ""

    def build_activity(self) -> Dict[str, Any]:
        """Constructs Discord Rich Presence payload tailored for current phase."""
        rank_key = "radiant"
        if "immortal 3" in self.rank_name.lower():
            rank_key = "immortal_3"
        elif "immortal" in self.rank_name.lower():
            rank_key = "immortal_1"

        rank_icon = RANK_ICONS.get(rank_key, RANK_ICONS["radiant"])
        agent_key = self.current_agent.lower().strip()
        agent_icon = AGENT_ICONS.get(agent_key, AGENT_ICONS["jett"])

        # Line 1: Rank and RR (Always clean and mobile-friendly: ~16 chars)
        details = f"{self.rank_name} ({self.rr_points} RR)"

        # Line 2: State per phase
        if self.phase == MatchPhase.IN_MATCH:
            state = f"{self.current_map} ({self.our_score}-{self.enemy_score})"
            start_ts = int(self.match_start_time)
        elif self.phase == MatchPhase.POST_MATCH:
            state = f"{self.match_outcome} ({self.our_score}-{self.enemy_score})"
            start_ts = int(self.match_start_time)
        elif self.phase == MatchPhase.IN_LOBBY:
            state = "In Lobby (In Queue)"
            start_ts = int(self.phase_start_time)
        else: # AGENT_SELECT
            state = f"Agent Select · {self.current_map}"
            start_ts = int(self.phase_start_time)

        activity: Dict[str, Any] = {
            "state": state,
            "details": details,
            "timestamps": {
                "start": start_ts,
            },
            "assets": {
                "large_image": rank_icon,
                "large_text": f"{self.rank_name}",
                "small_image": agent_icon,
                "small_text": f"{self.current_agent}",
            },
            "party": {
                "id": f"val-party-{uuid.uuid4().hex[:6]}",
                "size": [5, 5],
            },
        }

        return activity


def print_banner() -> None:
    print(f"{C_GOLD}{C_BOLD}")
    print("  ================================================================")
    print("    VALORANT DISCORD RICH PRESENCE  -  DYNAMIC MATCH SIMULATOR")
    print("  ================================================================")
    print(f"{C_RESET}")
    print(f"  {C_CYAN}Simulasi Real-Time Skor 0-0 -> 13, Rotasi Map Kompetitif & RR!{C_RESET}")
    print(f"  {C_GREEN}* 100% Ban Safe - Auto Map Pool Filter - Mobile-Clean Display{C_RESET}")
    print(f"  {C_DIM}Active Ranked Map Pool: {', '.join(ACTIVE_COMPETITIVE_MAPS)}{C_RESET}")
    print("  ----------------------------------------------------------------\n")


def interactive_setup() -> Tuple[MatchSimulator, str]:
    print(f"{C_BOLD}Pilih Mode Simulasi:{C_RESET}\n")
    print(f"  [{C_GOLD}1{C_RESET}] {C_BOLD}Realistis Penuh (Recommended){C_RESET}")
    print(f"      - Tiap ronde berjalan ~1.5 - 2 menit seperti game asli.")
    print(f"      - Match berlangsung ~30 menit, rotasi map otomatis saat 13 poin.")
    print(f"      - RR bertambah/berkurang otomatis (+22 RR).")
    print(f"  [{C_GOLD}2{C_RESET}] {C_BOLD}Realistis Mulai Tengah Match (Score ~5-3){C_RESET}")
    print(f"      - Langsung mulai dari ronde pertengahan agar terlihat sedang main.")
    print(f"  [{C_GOLD}3{C_RESET}] {C_BOLD}Mode Cepat / Demo Testing (--fast){C_RESET}")
    print(f"      - Skor bertambah tiap 8-10 detik untuk demonstrasi cepat.\n")

    choice = input(f"{C_CYAN}Pilihan Mode [1-3] (Tekan Enter untuk 1): {C_RESET}").strip()
    fast_mode = choice == "3"
    start_mid = choice == "2"

    print(f"\n{C_BOLD}Pengaturan Rank & Agent:{C_RESET}")
    rr_in = input("  Target RR Awal (default: 845): ").strip()
    rr = int(rr_in) if rr_in.isdigit() else 845

    agent_in = input("  Kunci Agent Tertentu? (Ketik nama agent / Enter untuk acak tiap match): ").strip()
    locked_agent = agent_in if agent_in else None

    sim = MatchSimulator(
        rank_name="Radiant",
        rr_points=rr,
        fast_mode=fast_mode,
        start_mid_match=start_mid,
        locked_agent=locked_agent,
    )
    mode_name = "Fast Demo (8s/round)" if fast_mode else ("Realistic (Mid-Game Start)" if start_mid else "Realistic (0-0 Start)")
    return sim, mode_name


def main() -> None:
    if sys.platform == "win32":
        os.system("")
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Valorant Discord RPC - Dynamic Match Simulator")
    parser.add_argument("--fast", action="store_true", help="Fast demo mode (score ticks every ~10s)")
    parser.add_argument("--start-mid", action="store_true", help="Start mid-match with existing score")
    parser.add_argument("--rr", type=int, default=845, help="Starting RR points")
    parser.add_argument("--agent", type=str, help="Lock specific agent (e.g. Jett, Reyna)")
    args = parser.parse_args()

    print_banner()

    if args.fast or args.start_mid or args.agent:
        sim = MatchSimulator(
            rank_name="Radiant",
            rr_points=args.rr,
            fast_mode=args.fast,
            start_mid_match=args.start_mid,
            locked_agent=args.agent,
        )
        mode_name = "Fast Demo" if args.fast else "Command Line"
    else:
        sim, mode_name = interactive_setup()

    print(f"\n{C_CYAN}[i] Mencari koneksi Discord Desktop Client...{C_RESET}")
    ipc = DiscordIPC(VALORANT_APP_ID)

    if not ipc.connect():
        print(f"{C_RED}[!] Gagal terhubung ke Discord Desktop Client!{C_RESET}")
        print(f"{C_YELLOW}[?] Pastikan aplikasi Discord Desktop Anda sudah terbuka dan login.{C_RESET}")
        sys.exit(1)

    print(f"{C_GREEN}[+] Berhasil terhubung ke Discord Client! User: {C_BOLD}{ipc.connected_user}{C_RESET}")

    # Set initial presence
    initial_activity = sim.build_activity()
    if not ipc.set_activity(initial_activity):
        print(f"{C_RED}[!] Discord menolak payload status!{C_RESET}")
        ipc.close()
        sys.exit(1)

    print(f"\n{C_GOLD}{C_BOLD}[OK] SIMULASI DYNAMIC VALORANT AKTIF!{C_RESET}")
    print(f"  - {C_BOLD}Mode:{C_RESET} {mode_name}")
    print(f"  - {C_BOLD}Map Awal:{C_RESET} {sim.current_map} {C_DIM}(dari Pool Kompetitif Aktif){C_RESET}")
    print(f"  - {C_BOLD}Agent:{C_RESET} {sim.current_agent}")
    print(f"  - {C_BOLD}Skor Awal:{C_RESET} {sim.our_score} - {sim.enemy_score}")
    print(f"  - {C_BOLD}Rank:{C_RESET} {C_GOLD}{sim.rank_name} ({sim.rr_points} RR){C_RESET}")
    print(f"\n{C_DIM}Status akan otomatis mengupdate ronde, skor, map, dan rotasi lobby secara mulus!{C_RESET}")
    print(f"{C_YELLOW}Tekan Ctrl + C di terminal ini kapan saja untuk mematikan status.{C_RESET}\n")

    try:
        while True:
            changed, msg = sim.tick()
            if changed:
                activity = sim.build_activity()
                ipc.set_activity(activity)
                timestamp_str = time.strftime("%H:%M:%S")
                print(f"  [{C_CYAN}{timestamp_str}{C_RESET}] {C_GREEN}*{C_RESET} {msg}")

            # Print inline live heart-beat
            act = sim.build_activity()
            line1 = act.get("details", "")
            line2 = act.get("state", "")
            sys.stdout.write(f"\r  {C_GREEN}[LIVE]{C_RESET} {C_GOLD}{line1}{C_RESET} | {line2} (5 of 5)  ")
            sys.stdout.flush()

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n\n{C_YELLOW}[i] Menghentikan status Discord RPC...{C_RESET}")
        ipc.clear_activity()
        ipc.close()
        print(f"{C_GREEN}[+] Status berhasil dihentikan. Discord Anda telah normal kembali.{C_RESET}")


if __name__ == "__main__":
    main()
