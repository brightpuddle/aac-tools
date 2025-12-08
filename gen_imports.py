#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from typing import TypedDict, cast


class ImportingDict(TypedDict):
    id: str


class ContentDict(TypedDict):
    dn: str
    class_name: str
    content: dict[str, str | None]


class ChangeDict(TypedDict):
    actions: list[str]
    before: ContentDict
    after: ContentDict | None
    importing: ImportingDict | None


class ResourceDict(TypedDict):
    address: str
    change: ChangeDict


class PlanDict(TypedDict):
    resource_changes: list[ResourceDict]


def write_import_blocks(fabric: str):
    with open(f"fabrics/{fabric}/plan.json") as f:
        tf_plan = cast(PlanDict, json.load(f))

    import_path = f"fabrics/{fabric}/import.tf"
    if os.path.exists(import_path):
        os.remove(import_path)
    with open(import_path, "w") as f:
        for change in tf_plan.get("resource_changes", []):
            if change.get("type") != "aci_rest_managed":
                continue
            if "create" not in change["change"].get("actions", []):
                continue
            address = change["address"]
            after = change["change"].get("after")
            if after is None:
                continue
            class_name = after["class_name"]
            dn = after["dn"]
            if ":" in dn:
                # Mirror ACI provider parsing function
                # We can't import objects with colons in the name
                brackets = 0
                skip = False
                for c in dn:
                    if c == "[":
                        brackets += 1
                    elif c == "]":
                        brackets -= 1
                    elif brackets > 0:
                        continue
                    elif c == ":":
                        skip = True
                        break
                if skip:
                    continue
            imp = f'import {{\n  to = {address}\n  id = "{class_name}:{dn}"\n}}\n\n'
            _ = f.write(imp)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <fabric>")
        sys.exit(1)
    write_import_blocks(sys.argv[-1])
