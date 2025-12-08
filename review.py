#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from functools import cached_property
from typing import Literal, TypedDict, cast, final

type Action = Literal["create", "update", "delete", "no-op"]


class ImportingDict(TypedDict):
    id: str


class ContentDict(TypedDict):
    dn: str
    content: dict[str, str | None]


class ChangeDict(TypedDict):
    actions: list[Action]
    before: ContentDict
    after: ContentDict
    importing: ImportingDict | None


class ResourceDict(TypedDict):
    address: str
    change: ChangeDict


class PlanDict(TypedDict):
    resource_changes: list[ResourceDict]


ignore_resources = [
    "module.aci.local_sensitive_file.defaults[0]",
    "module.aci.terraform_data.validation",
]


@final
class colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    END = "\033[0m"


@final
class Resource:
    def __init__(self, data: ResourceDict):
        self.data = data

    @cached_property
    def address(self):
        return self.data["address"]

    @cached_property
    def change(self) -> ChangeDict:
        return self.data["change"]

    @cached_property
    def action(self) -> Action:
        actions = self.change["actions"]
        return actions[0] if len(actions) == 1 else "no-op"

    @cached_property
    def before(self) -> dict[str, str]:
        # if "before" not in self.change or self.change["before"] is None:
        #     return {}
        content = self.change["before"].get("content", {})
        return {k: v for k, v in content.items() if v is not None}

    @cached_property
    def after(self) -> dict[str, str]:
        # if "after" not in self.change or self.change["after"] is None:
        #     return {}
        content = self.change["after"].get("content") or {}
        return {k: v for k, v in content.items() if v is not None}

    @cached_property
    def is_import(self) -> bool:
        if self.action != "update":
            return False
        importing = self.change.get("importing")
        if importing is None:
            return False
        return importing["id"] != ""

    @cached_property
    def fields(self) -> list[tuple[str, str, str]]:
        """Return the fields that are changing.
        (key, before, after)
        """
        fields: list[tuple[str, str, str]] = []
        match self.action:
            case "create":
                for k, v in self.after.items():
                    fields.append((k, "nil", v))
            case "update":
                for k, a in self.after.items():
                    b = self.before.get(k)
                    if b is None:
                        b = "nil"
                    if a == b:
                        continue
                    fields.append((k, b, a))
            case _:
                pass
        return fields

    def longest(self) -> int:
        longest = 0
        keys = [key for key, _, _ in self.fields]
        for key in keys:
            if len(key) > longest:
                longest = len(key)
        return longest

    def pad(self, key: str) -> str:
        padding = self.longest() - len(key)
        return key + (" " * padding)

    def print(self):
        match self.action:
            case "create":
                print(f"{colors.GREEN}{self.address}{colors.END}")
                for k, _, a in self.fields:
                    print(f"  {self.pad(k)} : '{a}'")
            case "update":
                print(f"{colors.YELLOW}{self.address}{colors.END}")
                for k, b, a in self.fields:
                    print(f"  {self.pad(k)} : '{b}' -> '{a}'")
            case "delete":
                print(f"{colors.RED}{self.address}{colors.END}")
            case "no-op":
                pass


def filter_action(changes: list[Resource], a: Action):
    """Exclude changes with action a"""
    return [res for res in changes if res.action != a]


def print_header(title: str):
    """Print a header with a title"""
    print()
    print("*" * 80)
    print(title)
    print("*" * 80)


def print_changes(resources: list[Resource]):
    for res in resources:
        res.print()


def review(fabric: str):
    with open(f"fabrics/{fabric}/plan.json") as f:
        plan = cast(PlanDict, json.load(f))
    resources: list[Resource] = []
    for resource in plan.get("resource_changes", []):
        res = Resource(resource)
        if res.action == "no-op":
            continue
        if res.address in ignore_resources:
            continue
        resources.append(res)

    all_updates = [res for res in resources if res.action == "update"]
    imports = [res for res in all_updates if res.is_import]
    updates = [res for res in all_updates if not res.is_import]
    creates = [res for res in resources if res.action == "create"]
    deletes = [res for res in resources if res.action == "delete"]

    if len(imports) > 0:
        print_header("Imports:")
        print_changes(imports)

    if len(creates) > 0:
        print_header("Creates:")
        print_changes(creates)

    if len(deletes) > 0:
        print_header("Deletes:")
        print_changes(deletes)

    if len(updates) > 0:
        print_header("Updates:")
        print_changes(updates)

    print_header("Summary:")
    print(f"Imports: {len(imports)}")
    print(f"Creates: {len(creates)}")
    print(f"Deletes: {len(deletes)}")
    print(f"Updates: {len(updates)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <fabric>")
        sys.exit(1)
    review(sys.argv[-1])
