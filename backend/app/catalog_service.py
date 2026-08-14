import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CATALOG_DIRECTORY = (
    PROJECT_ROOT
    / "catalog"
    / "devices"
)


def load_device_file(file_path):
    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        device = json.load(file)

    device["_catalog_file"] = str(
        file_path.relative_to(PROJECT_ROOT)
    )

    return device


def get_devices():
    devices = []
    device_ids = set()

    if not CATALOG_DIRECTORY.exists():
        return []

    for file_path in sorted(
        CATALOG_DIRECTORY.rglob("*.json")
    ):
        device = load_device_file(file_path)

        device_id = device.get("id")

        if not device_id:
            raise RuntimeError(
                f"Device sem id: {file_path}"
            )

        if device_id in device_ids:
            raise RuntimeError(
                f"Device id duplicado: {device_id}"
            )

        device_ids.add(device_id)
        devices.append(device)

    return sorted(
        devices,
        key=lambda item: (
            item.get("category", ""),
            item.get("vendor", ""),
            item.get("name", ""),
        ),
    )


def get_device(device_id):
    for device in get_devices():
        if device["id"] == device_id:
            return device

    return None
