from __future__ import annotations

import difflib
from typing import List, Tuple


class DiffGenerator:
    def __init__(self, source_sql: str, target_sql: str) -> None:
        self.source = (source_sql or "").splitlines()
        self.target = (target_sql or "").splitlines()

    def side_by_side(self) -> List[Tuple[str, str, str]]:
        """Return list of tuples: (left_line, right_line, tag)
        tag: 'same', 'add' (source only), 'del' (target only), 'chg' (different)
        """
        matcher = difflib.SequenceMatcher(a=self.source, b=self.target)
        output: List[Tuple[str, str, str]] = []
        for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
            if opcode == "equal":
                for i in range(a0, a1):
                    output.append((self.source[i], self.target[b0 + (i - a0)], "same"))
            elif opcode == "insert":
                for j in range(b0, b1):
                    output.append(("", self.target[j], "del"))
            elif opcode == "delete":
                for i in range(a0, a1):
                    output.append((self.source[i], "", "add"))
            elif opcode == "replace":
                max_len = max(a1 - a0, b1 - b0)
                for k in range(max_len):
                    left = self.source[a0 + k] if a0 + k < a1 else ""
                    right = self.target[b0 + k] if b0 + k < b1 else ""
                    output.append((left, right, "chg"))
        return output
