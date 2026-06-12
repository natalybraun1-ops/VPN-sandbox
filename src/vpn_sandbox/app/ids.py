from __future__ import annotations

from uuid import uuid4


class UuidFactory:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex}"
