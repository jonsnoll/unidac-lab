import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from app.catalog_service import get_device


PROJECT_ROOT = Path(__file__).resolve().parents[2]

IMAGE_STORE = (
    PROJECT_ROOT
    / "images"
    / "store"
)

METADATA_DIRECTORY = (
    PROJECT_ROOT
    / "images"
    / "metadata"
)


SAFE_ID = re.compile(
    r"^[a-z0-9][a-z0-9-]{1,62}$"
)


def validate_identifier(value, field_name):
    if not SAFE_ID.match(value):
        raise ValueError(
            f"{field_name} invalido: {value}"
        )


def calculate_sha256(file_path):
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        while True:
            chunk = file.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def inspect_qcow2(file_path):
    result = subprocess.run(
        [
            "qemu-img",
            "info",
            "--output=json",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    info = json.loads(
        result.stdout
    )

    if info.get("format") != "qcow2":
        raise ValueError(
            "Arquivo nao e QCOW2 valido"
        )

    return {
        "virtual_size_bytes":
            info.get("virtual-size"),
        "actual_size_bytes":
            info.get("actual-size"),
    }


def import_image(
    *,
    source_file,
    image_id,
    name,
    vendor,
    version,
    template_id,
    image_format,
):
    validate_identifier(
        image_id,
        "image_id",
    )

    validate_identifier(
        vendor,
        "vendor",
    )

    template = get_device(
        template_id
    )

    if template is None:
        raise ValueError(
            "Template nao encontrado: "
            f"{template_id}"
        )

    allowed_formats = (
        template.get(
            "image_types",
            []
        )
    )

    if (
        allowed_formats
        and
        image_format
        not in allowed_formats
    ):
        raise ValueError(
            f"Formato {image_format} "
            "nao permitido para "
            f"{template_id}"
        )

    metadata_path = (
        METADATA_DIRECTORY
        / f"{image_id}.json"
    )

    if metadata_path.exists():
        raise ValueError(
            f"Image id ja existe: "
            f"{image_id}"
        )

    destination_directory = (
        IMAGE_STORE
        / vendor
        / image_id
    )

    destination_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    extension = image_format

    destination_file = (
        destination_directory
        / f"base.{extension}"
    )

    try:
        with destination_file.open(
            "wb"
        ) as output_file:
            shutil.copyfileobj(
                source_file,
                output_file,
                length=1024 * 1024,
            )

        image_info = {}

        if image_format == "qcow2":
            image_info = inspect_qcow2(
                destination_file
            )

        elif image_format == "iso":
            image_info = {
                "file_size_bytes":
                    destination_file
                    .stat()
                    .st_size,
            }

        elif image_format in (
            "raw",
            "img",
        ):
            image_info = {
                "file_size_bytes":
                    destination_file
                    .stat()
                    .st_size,
            }

        sha256 = calculate_sha256(
            destination_file
        )

        destination_file.chmod(
            0o444
        )

        metadata = {
            "schema_version": 1,
            "id": image_id,
            "name": name,
            "vendor": vendor,
            "version": version,
            "kind": (
                "installation-media"
                if image_format == "iso"
                else "disk-image"
            ),
            "format": image_format,
            "deployment": (
                "iso-install"
                if image_format == "iso"
                else (
                    "qcow2-overlay"
                    if image_format == "qcow2"
                    else "disk-copy"
                )
            ),
            "description": (
                f"Imagem importada para "
                f"{template_id}."
            ),
            "compatible_templates": [
                template_id
            ],
            "storage": {
                "relative_path": str(
                    destination_file
                    .relative_to(
                        PROJECT_ROOT
                    )
                ),
                "read_only_base": True,
            },
            "integrity": {
                "sha256": sha256,
            },
            "image_info": image_info,
        }

        METADATA_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_metadata = (
            metadata_path.with_suffix(
                ".json.tmp"
            )
        )

        with temporary_metadata.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                metadata,
                file,
                indent=2,
            )

        temporary_metadata.replace(
            metadata_path
        )

        return metadata

    except Exception:
        if destination_directory.exists():
            shutil.rmtree(
                destination_directory
            )

        raise
