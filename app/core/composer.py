from __future__ import annotations

from app.composers.models import ComposedMessage
from app.composers.registry import ComposerRegistry


# Alias Composer to ComposerRegistry for backward compatibility
Composer = ComposerRegistry

__all__ = ["Composer", "ComposedMessage"]
