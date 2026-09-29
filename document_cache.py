from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class _CacheEntry:
    contents: Any
    timestamp: float  # when it was cached
    file_mtime: Optional[float]  # file modification time at cache insert


class DocumentCache:
    """
    In-memory cache for processed documents (e.g., PDF pages).

    Features:
    - TTL-based expiration (default: 1 hour).
    - Keyed by absolute file path + file modification time, so:
      * If the file changes on disk, old cache entries are ignored.
    - Simple API:
        - add_document(file_path, contents)
        - get_document(file_path) -> contents | None
        - clear_expired()
    """

    def __init__(self, ttl: int = 3600) -> None:
        """
        :param ttl: Time-to-live in seconds for each cached document.
                    Default is 3600 seconds (1 hour).
        """
        self.ttl: int = int(ttl)
        # key: str (hash), value: _CacheEntry
        self._cache: Dict[str, _CacheEntry] = {}

    def _normalize_path(self, file_path: str | Path) -> str:
        """
        Normalize to an absolute, resolved POSIX-like string to avoid
        duplicate cache entries for the same file.
        """
        p = Path(file_path).expanduser().resolve()
        return p.as_posix()

    def _get_file_mtime(self, file_path: str) -> Optional[float]:
        """
        Safely get the file's modification time.

        Returns:
            float: mtime if file exists
            None : if file does not exist or stat fails
        """
        try:
            return Path(file_path).stat().st_mtime
        except OSError:
            return None

    def _get_key(self, file_path: str) -> str:
        """
        Build a stable key from normalized path and file mtime.

        If mtime is unavailable, falls back to path-only hash.
        """
        norm_path = self._normalize_path(file_path)
        mtime = self._get_file_mtime(norm_path)
        base = f"{norm_path}|{mtime}" if mtime is not None else norm_path
        return hashlib.md5(base.encode("utf-8")).hexdigest()

    def add_document(self, file_path: str | Path, contents: Any) -> None:
        """
        Cache the processed contents of a document.

        :param file_path: Path to the source file.
        :param contents:  Arbitrary processed representation (e.g. list of pages).
        """
        norm_path = self._normalize_path(file_path)
        key = self._get_key(norm_path)
        file_mtime = self._get_file_mtime(norm_path)
        self._cache[key] = _CacheEntry(
            contents=contents,
            timestamp=time.time(),
            file_mtime=file_mtime,
        )

    def get_document(self, file_path: str | Path) -> Optional[Any]:
        """
        Retrieve cached contents if present, not expired,
        and still matching the current file on disk.

        :param file_path: Path to the source file.
        :return: Cached contents or None if missing/expired/stale.
        """
        norm_path = self._normalize_path(file_path)
        key = self._get_key(norm_path)
        entry = self._cache.get(key)
        if not entry:
            return None

        # TTL check
        now = time.time()
        if (now - entry.timestamp) > self.ttl:
            # Expired – remove and miss
            del self._cache[key]
            return None

        # File-changed check: if file mtime differs, treat as stale
        current_mtime = self._get_file_mtime(norm_path)
        if entry.file_mtime is not None and current_mtime is not None:
            if current_mtime != entry.file_mtime:
                # Underlying file changed – drop the stale cache entry
                del self._cache[key]
                return None

        return entry.contents

    def clear_expired(self) -> None:
        """
        Remove all entries whose TTL has elapsed.
        """
        now = time.time()
        expired_keys = [
            k
            for k, v in self._cache.items()
            if (now - v.timestamp) > self.ttl
        ]
        for k in expired_keys:
            del self._cache[k]

    def clear_all(self) -> None:
        """
        Remove all cached entries.
        """
        self._cache.clear()

    def __len__(self) -> int:
        """
        :return: Number of cached entries (not counting expired-but-not-yet-cleared).
        """
        return len(self._cache)
