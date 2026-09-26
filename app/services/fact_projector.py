from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.context import ContextBundle
from app.policies.triggers import FactSpec


@dataclass(frozen=True)
class Fact:
    id: str
    value: str
    priority: int


class FactProjector:
    """
    Project only policy-approved facts from runtime context.

    Supports:
        exact paths
        terminal wildcard paths

    Example:
        merchant.performance.*
        trigger.payload.*
        customer.relationship.*
    """

    def project(
        self,
        context: ContextBundle,
        specs: tuple[FactSpec, ...],
        max_facts: int = 20,
    ) -> list[Fact]:

        sources = {
            "trigger": context.trigger.payload,
            "merchant": context.merchant.payload,
            "category": context.category.payload,
        }

        if context.customer is not None:
            sources["customer"] = (
                context.customer.payload
            )

        candidates: dict[str, Fact] = {}

        for spec in specs:
            values = self._resolve(
                sources,
                spec.path,
            )

            for fact_id, value in values[:spec.limit]:

                if value is None:
                    continue

                text = self._stringify(
                    value
                )

                if not text:
                    continue

                existing = candidates.get(
                    fact_id
                )

                fact = Fact(
                    id=fact_id,
                    value=text,
                    priority=spec.priority,
                )

                if (
                    existing is None
                    or fact.priority > existing.priority
                ):
                    candidates[fact_id] = fact

        return sorted(
            candidates.values(),
            key=lambda fact: (
                -fact.priority,
                fact.id,
            ),
        )[:max_facts]

    def _resolve(
        self,
        sources: dict[str, Any],
        path: str,
    ) -> list[tuple[str, Any]]:

        parts = path.split(".")

        root = parts[0]

        if root not in sources:
            return []

        current = sources[root]

        return self._walk(
            current,
            parts[1:],
            root,
        )

    def _walk(
        self,
        value: Any,
        parts: list[str],
        prefix: str,
    ) -> list[tuple[str, Any]]:

        if not parts:
            return [
                (prefix, value)
            ]

        part = parts[0]

        if part == "*":

            results: list[
                tuple[str, Any]
            ] = []

            if isinstance(
                value,
                dict,
            ):

                for key, child in value.items():
                    results.extend(
                        self._walk(
                            child,
                            parts[1:],
                            f"{prefix}.{key}",
                        )
                    )

            elif isinstance(
                value,
                list,
            ):

                for index, child in enumerate(
                    value
                ):
                    results.extend(
                        self._walk(
                            child,
                            parts[1:],
                            f"{prefix}.{index}",
                        )
                    )

            return results

        if isinstance(
            value,
            dict,
        ) and part in value:

            return self._walk(
                value[part],
                parts[1:],
                f"{prefix}.{part}",
            )

        if isinstance(
            value,
            list,
        ):
            try:
                index = int(part)
            except ValueError:
                return []

            if 0 <= index < len(value):
                return self._walk(
                    value[index],
                    parts[1:],
                    f"{prefix}.{index}",
                )

        return []

    @staticmethod
    def _stringify(
        value: Any,
    ) -> str:

        if isinstance(
            value,
            (dict, list),
        ):
            import json

            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        return str(value).strip()
