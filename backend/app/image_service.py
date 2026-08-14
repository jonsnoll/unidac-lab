import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

METADATA_DIRECTORY = (
    PROJECT_ROOT
    / "images"
    / "metadata"
)


def load_image_file(file_path):
    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        image = json.load(file)

    storage = image.get(
        "storage",
        {},
    )

    relative_path = storage.get(
        "relative_path"
    )

    image_path = None
    available = False
    file_size_bytes = None

    if relative_path:
        image_path = (
            PROJECT_ROOT
            / relative_path
        )

        available = (
            image_path.is_file()
        )

        if available:
            file_size_bytes = (
                image_path.stat().st_size
            )

    image["_metadata_file"] = str(
        file_path.relative_to(
            PROJECT_ROOT
        )
    )

    image["available"] = available
    image["file_size_bytes"] = (
        file_size_bytes
    )

    return image


def get_images(template_id=None):
    images = []
    image_ids = set()

    if not METADATA_DIRECTORY.exists():
        return []

    for file_path in sorted(
        METADATA_DIRECTORY.rglob(
            "*.json"
        )
    ):
        image = load_image_file(
            file_path
        )

        image_id = image.get("id")

        if not image_id:
            raise RuntimeError(
                f"Image sem id: {file_path}"
            )

        if image_id in image_ids:
            raise RuntimeError(
                f"Image id duplicado: {image_id}"
            )

        image_ids.add(image_id)

        if template_id:
            compatible = image.get(
                "compatible_templates",
                [],
            )

            if template_id not in compatible:
                continue

        images.append(image)

    return sorted(
        images,
        key=lambda item: (
            item.get("vendor", ""),
            item.get("name", ""),
        ),
    )


def get_image(image_id):
    for image in get_images():
        if image["id"] == image_id:
            return image

    return None
