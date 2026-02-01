from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any


class ProjectManager:
    """Save/load simple project files with source/target and filter settings."""

    def save(self, data: Dict[str, Any], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        root = ET.Element("SQLCompareProject")

        def add_conn(parent, label, info):
            node = ET.SubElement(parent, label)
            ET.SubElement(node, "Server").text = info.get("server", "")
            ET.SubElement(node, "Database").text = info.get("database", "")
            ET.SubElement(node, "Auth").text = info.get("auth", "")
            ET.SubElement(node, "Username").text = info.get("username", "")
        add_conn(root, "Source", data.get("source", {}))
        add_conn(root, "Target", data.get("target", {}))

        filters = data.get("filters", {})
        fil_node = ET.SubElement(root, "Filters")
        for k, v in filters.items():
            ET.SubElement(fil_node, k).text = str(v)

        tree = ET.ElementTree(root)
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def load(self, path: Path) -> Dict[str, Any]:
        tree = ET.parse(path)
        root = tree.getroot()

        def read_conn(label):
            node = root.find(label)
            if node is None:
                return {}
            return {
                "server": (node.findtext("Server") or ""),
                "database": (node.findtext("Database") or ""),
                "auth": (node.findtext("Auth") or ""),
                "username": (node.findtext("Username") or ""),
            }

        filters = {}
        fil_node = root.find("Filters")
        if fil_node is not None:
            for child in fil_node:
                filters[child.tag] = child.text

        return {
            "source": read_conn("Source"),
            "target": read_conn("Target"),
            "filters": filters,
        }
