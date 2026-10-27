"""Trip persistence: Supabase when configured, otherwise a local JSON file."""
from __future__ import annotations

import json
import threading
from functools import lru_cache
from typing import Any, Dict, List, Optional, Protocol

from . import config


class Store(Protocol):
    name: str

    def list(self, user_id: str) -> List[Dict[str, Any]]: ...
    def get(self, user_id: str, trip_id: str) -> Optional[Dict[str, Any]]: ...
    def save(self, trip: Dict[str, Any]) -> None: ...
    def delete(self, user_id: str, trip_id: str) -> bool: ...


class LocalStore:
    name = "local"

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}")

    def _read(self) -> Dict[str, Dict[str, Any]]:
        try:
            return json.loads(self.path.read_text() or "{}")
        except json.JSONDecodeError:
            return {}

    def _write(self, data: Dict[str, Dict[str, Any]]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self.path)

    def list(self, user_id):
        with self._lock:
            trips = [t for t in self._read().values() if t["user_id"] == user_id]
        return sorted(trips, key=lambda t: t["updated_at"], reverse=True)

    def get(self, user_id, trip_id):
        with self._lock:
            t = self._read().get(trip_id)
        return t if t and t["user_id"] == user_id else None

    def save(self, trip):
        with self._lock:
            data = self._read()
            data[trip["id"]] = trip
            self._write(data)

    def delete(self, user_id, trip_id):
        with self._lock:
            data = self._read()
            t = data.get(trip_id)
            if not t or t["user_id"] != user_id:
                return False
            del data[trip_id]
            self._write(data)
            return True


class SupabaseStore:
    name = "supabase"

    def __init__(self, url: str, key: str):
        from supabase import create_client  # imported lazily so local mode needs no extra install

        self.client = create_client(url, key)

    def _table(self):
        return self.client.table("trips")

    def list(self, user_id):
        res = self._table().select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
        return res.data or []

    def get(self, user_id, trip_id):
        res = self._table().select("*").eq("id", trip_id).eq("user_id", user_id).limit(1).execute()
        return res.data[0] if res.data else None

    def save(self, trip):
        self._table().upsert(trip).execute()

    def delete(self, user_id, trip_id):
        res = self._table().delete().eq("id", trip_id).eq("user_id", user_id).execute()
        return bool(res.data)


@lru_cache(maxsize=1)
def get_store() -> Store:
    if config.supabase_enabled():
        return SupabaseStore(config.SUPABASE_URL, config.SUPABASE_KEY)
    return LocalStore(config.LOCAL_DATA_FILE)


@lru_cache(maxsize=1)
def supabase_client():
    from supabase import create_client

    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
