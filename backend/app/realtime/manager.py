from supabase import Client
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from uuid import uuid4


class LobbyPresence:
    """Ephemeral waiting room presence for the single-worker development server."""
    def __init__(self, clock=monotonic, ttl=30):
        self.clock, self.ttl = clock, ttl
        self.entries = {}
        self.lock = Lock()

    def touch(self, employee_id):
        with self.lock:
            now = self.clock()
            self._prune(now)
            entry = self.entries.setdefault(employee_id, {
                "id": str(uuid4()), "joinedAt": datetime.now(timezone.utc).isoformat(),
            })
            entry["seen"] = now

    def discard(self, employee_id):
        with self.lock:
            self.entries.pop(employee_id, None)

    def _prune(self, now):
        self.entries = {key: value for key, value in self.entries.items()
                        if now - value["seen"] < self.ttl}

    def snapshot(self):
        with self.lock:
            self._prune(self.clock())
            return {key: dict(value) for key, value in self.entries.items()}


lobby_presence = LobbyPresence()


class RealtimeManager:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.channels = {}

    def get_channel(self, game_id: str):
        """Get or create a realtime channel for a game."""
        if game_id not in self.channels:
            self.channels[game_id] = self.supabase.channel(f"game:{game_id}")
        return self.channels[game_id]

    async def send(self, game_id: str, event: str, payload: dict) -> None:
        """Send a realtime event to a game channel."""
        channel = self.get_channel(game_id)
        channel.send({
            "event": event,
            "payload": payload,
        })

    async def subscribe(self, game_id: str, event: str, callback) -> None:
        """Subscribe to a specific event on a game channel."""
        channel = self.get_channel(game_id)
        channel.on(event, callback)
        channel.subscribe()
