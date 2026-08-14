import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

LAB_DIRECTORY = (
    PROJECT_ROOT
    / "labs"
    / "vxlan-fgt-01"
)

LAYOUT_FILE = (
    LAB_DIRECTORY
    / "layout.json"
)


def get_layout():
    if not LAYOUT_FILE.exists():
        return {
            "nodes": [],
        }

    with LAYOUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_layout(layout):
    LAB_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = (
        LAYOUT_FILE.with_suffix(".json.tmp")
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            layout,
            file,
            indent=2,
        )

    temporary_file.replace(
        LAYOUT_FILE
    )

    return layout
