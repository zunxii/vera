from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class StoredContext:
    scope: str
    context_id: str
    version: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class ContextWriteResult:
    """
    Result of attempting to write a context.
    """

    accepted: bool
    replay: bool
    current_version: int | None


class ContextStore:
    """
    Thread-safe runtime store for judge-provided context.

    Version semantics:

    No existing context
        -> accept

    Same version
        -> idempotent success, do not mutate

    Higher version
        -> atomically replace

    Lower version
        -> reject as stale
    """

    VALID_SCOPES = frozenset(
        {
            "category",
            "merchant",
            "customer",
            "trigger",
        }
    )

    def __init__(self) -> None:
        self._contexts: dict[
            tuple[str, str],
            StoredContext,
        ] = {}

        self._lock = RLock()

    def put(
        self,
        *,
        scope: str,
        context_id: str,
        version: int,
        payload: dict[str, Any],
    ) -> ContextWriteResult:
        """
        Store a context according to version semantics.

        This operation is atomic with respect to other writes.
        """

        key = (scope, context_id)

        with self._lock:
            current = self._contexts.get(key)

            # First version.
            if current is None:
                self._contexts[key] = StoredContext(
                    scope=scope,
                    context_id=context_id,
                    version=version,
                    payload=dict(payload),
                )

                return ContextWriteResult(
                    accepted=True,
                    replay=False,
                    current_version=version,
                )

            # Exact replay.
            #
            # IMPORTANT:
            # The challenge defines this as idempotent success.
            if version == current.version:
                return ContextWriteResult(
                    accepted=True,
                    replay=True,
                    current_version=current.version,
                )

            # Older version.
            if version < current.version:
                return ContextWriteResult(
                    accepted=False,
                    replay=False,
                    current_version=current.version,
                )

            # Strictly newer version.
            self._contexts[key] = StoredContext(
                scope=scope,
                context_id=context_id,
                version=version,
                payload=dict(payload),
            )

            return ContextWriteResult(
                accepted=True,
                replay=False,
                current_version=version,
            )

    def get(
        self,
        scope: str,
        context_id: str,
    ) -> StoredContext | None:
        with self._lock:
            return self._contexts.get(
                (scope, context_id)
            )

    def get_payload(
        self,
        scope: str,
        context_id: str,
    ) -> dict[str, Any] | None:
        context = self.get(
            scope,
            context_id,
        )

        if context is None:
            return None

        return dict(context.payload)

    def has(
        self,
        scope: str,
        context_id: str,
    ) -> bool:
        return self.get(
            scope,
            context_id,
        ) is not None

    def counts(self) -> dict[str, int]:
        counts = {
            scope: 0
            for scope in self.VALID_SCOPES
        }

        with self._lock:
            for scope, _ in self._contexts:
                counts[scope] += 1

        return counts

    def clear(self) -> None:
        with self._lock:
            self._contexts.clear()

    def snapshot(self) -> list[StoredContext]:
        """
        Return a consistent point-in-time snapshot.

        Useful for diagnostics and tests.
        """

        with self._lock:
            return list(
                self._contexts.values()
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._contexts)
