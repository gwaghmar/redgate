from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any


def load_script_folder(root: str | Path) -> Dict[str, Any]:
    """Load T-SQL scripts from a folder into a metadata dict.

    This provides a lightweight metadata representation compatible with
    the structures returned by MetadataExtractor.extract, focusing on
    object definitions (tables, views, procedures, functions, triggers,
    synonyms). Column-level details are not inferred; comparisons are
    performed on raw definitions.
    """

    base = Path(root)
    if not base.is_dir():
        raise ValueError(f"Scripts folder not found: {base}")

    metadata: Dict[str, Any] = {
        "tables": {},
        "views": {},
        "procedures": {},
        "functions": {},
        "triggers": {},
        "synonyms": {},
    }

    pattern = re.compile(
        r"create\s+(or\s+alter\s+)?"
        r"(table|view|procedure|proc|function|trigger|synonym)\s+"
        r"(?P<fullname>[^\s(]+)",
        re.IGNORECASE,
    )

    for sql_file in base.rglob("*.sql"):
        try:
            sql_text = sql_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            sql_text = sql_file.read_text(encoding="latin-1", errors="ignore")

        match = pattern.search(sql_text)
        if not match:
            continue

        obj_type = match.group(2).lower()
        fullname = match.group("fullname").strip()

        # Normalise object name to schema.name format
        fullname = fullname.strip("[]")
        if "." not in fullname:
            fullname = f"dbo.{fullname}"

        entry = {"definition": sql_text}

        if obj_type == "table":
            metadata.setdefault("tables", {})[fullname] = entry
        elif obj_type == "view":
            metadata.setdefault("views", {})[fullname] = entry
        elif obj_type in ("procedure", "proc"):
            metadata.setdefault("procedures", {})[fullname] = entry
        elif obj_type == "function":
            metadata.setdefault("functions", {})[fullname] = entry
        elif obj_type == "trigger":
            metadata.setdefault("triggers", {})[fullname] = entry
        elif obj_type == "synonym":
            metadata.setdefault("synonyms", {})[fullname] = entry

    return metadata
