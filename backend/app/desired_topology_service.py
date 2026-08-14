import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

LAB_DIRECTORY = (
    PROJECT_ROOT
    / "labs"
    / "vxlan-fgt-01"
)

DESIRED_FILE = (
    LAB_DIRECTORY
    / "desired_topology.json"
)


def empty_topology():
    return {
        "schema_version": 1,
        "nodes": [],
        "links": [],
    }


def get_desired_topology():
    if not DESIRED_FILE.exists():
        return empty_topology()

    with DESIRED_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_desired_topology(topology):
    LAB_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = (
        DESIRED_FILE.with_suffix(
            ".json.tmp"
        )
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            topology,
            file,
            indent=2,
        )

    temporary_file.replace(
        DESIRED_FILE
    )

    return topology
