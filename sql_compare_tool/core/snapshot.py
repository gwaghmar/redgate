from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


SNAPSHOT_VERSION = 1


def save_snapshot(path: str | Path, metadata: Dict[str, Any]) -> None:
    """Save schema metadata to a snapshot file.

    The snapshot is a simple JSON document with a version header and a
    "metadata" payload so the format can evolve without breaking older
    files.
    """

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": SNAPSHOT_VERSION, "metadata": metadata}
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def load_snapshot(path: str | Path) -> Dict[str, Any]:
    """Load schema metadata from a snapshot file.

    Accepts both the new wrapped format {"version": .., "metadata": ..}
    and a plain JSON metadata dict (for maximum compatibility).
    """

    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "metadata" in data:
        return data["metadata"]  # type: ignore[return-value]
    # Fallback: treat the whole document as metadata
    if isinstance(data, dict):
        return data  # type: ignore[return-value]
    raise ValueError("Snapshot file does not contain a metadata object")
