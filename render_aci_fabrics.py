#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

import yaml
from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.environment import Environment

env = Environment(undefined=StrictUndefined)
env.loader = FileSystemLoader("./templates/")

VARIABLE_FILE = "vars.yaml"
TEMPLATE_DIR = "templates"


def render(fabric: str):
    print(f"Rendering files for {fabric}...")
    with open(f"fabrics/{fabric}/{VARIABLE_FILE}", "r") as f:
        vars = yaml.safe_load(f)  # pyright: ignore[reportAny]

    for file in os.listdir(TEMPLATE_DIR):
        base_name = file.split(".")[0]
        print(f"  Rendering {file} to {base_name}.rendered.nac.yaml")
        template = env.get_template(file)
        rendered = template.render(**vars)
        with open(f"fabrics/{fabric}/data/{base_name}.rendered.nac.yaml", "w") as out:
            _ = out.write(rendered)
    print(f"{fabric} rendering complete!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <fabric>")
        sys.exit(1)
    render(sys.argv[-1])
