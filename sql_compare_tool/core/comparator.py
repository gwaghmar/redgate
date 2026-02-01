from __future__ import annotations

from typing import Dict, Any, List

from deepdiff import DeepDiff


STATUS = {
    "IDENTICAL": "IDENTICAL",
    "DIFFERENT": "DIFFERENT",
    "MISSING_IN_TARGET": "MISSING_IN_TARGET",
    "MISSING_IN_SOURCE": "MISSING_IN_SOURCE",
}


class SchemaComparator:
    def __init__(self, source: Dict[str, Dict[str, Any]], target: Dict[str, Dict[str, Any]]) -> None:
        self.source = source
        self.target = target

    def compare(self) -> Dict[str, List[Dict[str, Any]]]:
        results: Dict[str, List[Dict[str, Any]]] = {}
        for obj_type in [
            "tables",
            "views",
            "procedures",
            "functions",
            "triggers",
            "users",
            "roles",
            "schemas",
            "synonyms",
            "extended_properties",
            "check_constraints",
            "default_constraints",
            "unique_constraints",
            "user_defined_types",
            "sequences",
        ]:
            src_objs = self.source.get(obj_type, {})
            tgt_objs = self.target.get(obj_type, {})
            all_keys = set(src_objs.keys()) | set(tgt_objs.keys())
            items: List[Dict[str, Any]] = []
            for key in sorted(all_keys):
                src = src_objs.get(key)
                tgt = tgt_objs.get(key)
                if src and not tgt:
                    items.append({"name": key, "status": STATUS["MISSING_IN_TARGET"], "details": src})
                elif tgt and not src:
                    items.append({"name": key, "status": STATUS["MISSING_IN_SOURCE"], "details": tgt})
                else:
                    diff = self._diff(src, tgt)
                    if not diff:
                        items.append({"name": key, "status": STATUS["IDENTICAL"], "details": src})
                    else:
                        items.append({"name": key, "status": STATUS["DIFFERENT"], "details": {"source": src, "target": tgt, "diff": diff}})
            results[obj_type] = items
        return results

    @staticmethod
    def summarize(results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        summary = {k: 0 for k in STATUS.values()}
        for items in results.values():
            for item in items:
                summary[item["status"]] += 1
        return summary

    @staticmethod
    def _diff(src: Any, tgt: Any) -> str:
        diff = DeepDiff(src, tgt, ignore_order=True)
        return diff.to_json() if diff else ""
