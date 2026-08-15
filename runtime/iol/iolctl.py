#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


DEFAULT_RUNTIME_IMAGE = (
    "unidac-lab-iol-runtime:0.4-dev"
)

DEFAULT_LICENSE_FILE = Path(
    "/etc/unidac-lab/iol/iourc"
)

DEFAULT_STATE_DIR = Path(
    "/var/lib/unidac-lab/iol"
)

INSTANCE_RE = re.compile(
    r"^ulab-iol-[a-z0-9][a-z0-9-]{0,47}$"
)


class IolError(RuntimeError):
    pass


def fail(message):
    raise IolError(message)


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def docker_binary():
    value = shutil.which(
        "docker"
    )

    if not value:
        fail(
            "docker nao encontrado."
        )

    return value


def validate_image(path):
    path = path.resolve()

    if not path.is_file():
        fail(
            f"Imagem nao encontrada: {path}"
        )

    if path.stat().st_size <= 0:
        fail(
            "Imagem esta vazia."
        )

    process = subprocess.run(
        [
            "file",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    output = (
        process.stdout
        + process.stderr
    ).strip()

    if process.returncode != 0:
        fail(
            "Falha ao identificar imagem: "
            + output
        )

    expected = (
        "ELF 32-bit LSB executable, "
        "Intel 80386"
    )

    if expected not in output:
        fail(
            "Imagem nao corresponde ao "
            "IOL ELF32 esperado: "
            + output
        )

    return {
        "path":
            str(path),

        "size_bytes":
            path.stat().st_size,

        "sha256":
            sha256_file(
                path
            ),

        "file":
            output,
    }


def inspect_license(path):
    path = path.resolve()

    if not path.exists():
        return {
            "configured":
                False,

            "path":
                str(path),

            "reason":
                (
                    "Arquivo de licenca "
                    "nao configurado."
                ),
        }

    if not path.is_file():
        return {
            "configured":
                False,

            "path":
                str(path),

            "reason":
                "Caminho nao e arquivo.",
        }

    stat = path.stat()

    mode = stat.st_mode & 0o777

    if stat.st_uid != 0:
        return {
            "configured":
                False,

            "path":
                str(path),

            "reason":
                "Arquivo deve pertencer a root.",
        }

    if mode & 0o077:
        return {
            "configured":
                False,

            "path":
                str(path),

            "reason":
                (
                    "Arquivo deve ter permissao "
                    "0600 ou mais restritiva."
                ),
        }

    if stat.st_size <= 0:
        return {
            "configured":
                False,

            "path":
                str(path),

            "reason":
                "Arquivo esta vazio.",
        }

    return {
        "configured":
            True,

        "path":
            str(path),

        "size_bytes":
            stat.st_size,

        "owner_uid":
            stat.st_uid,

        "mode":
            oct(mode),

        "note":
            (
                "Conteudo nao foi exibido "
                "nem alterado."
            ),
    }


def runtime_image_exists(
    runtime_image,
):
    process = subprocess.run(
        [
            docker_binary(),
            "image",
            "inspect",
            runtime_image,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=20,
    )

    return (
        process.returncode == 0
    )


def compatibility_check(
    image,
    runtime_image,
):
    image = image.resolve()

    if not runtime_image_exists(
        runtime_image
    ):
        fail(
            "Imagem do sandbox IOL nao "
            f"existe: {runtime_image}"
        )

    process = subprocess.run(
        [
            docker_binary(),
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "-v",
            (
                f"{image}:"
                "/images/base.bin:ro"
            ),
            runtime_image,
            "/images/base.bin",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    output = (
        process.stdout
        + process.stderr
    )

    if (
        process.returncode != 0
        or
        "IOL COMPAT SANDBOX = PASS"
        not in output
    ):
        fail(
            "Sandbox de compatibilidade "
            "falhou:\n"
            + output
        )

    return {
        "status":
            "pass",

        "runtime_image":
            runtime_image,

        "ios_started":
            False,
    }


def ensure_state_dirs(
    state_dir,
):
    instances = (
        state_dir
        / "instances"
    )

    instances.mkdir(
        parents=True,
        exist_ok=True,
    )

    os.chmod(
        state_dir,
        0o755,
    )

    os.chmod(
        instances,
        0o755,
    )

    return instances


def validate_instance_name(
    value,
):
    if not INSTANCE_RE.fullmatch(
        value
    ):
        fail(
            "Nome de instancia invalido. "
            "Use ulab-iol- seguido por "
            "letras minusculas, numeros "
            "e hifens."
        )

    return value


def manifest_path(
    state_dir,
    instance,
):
    return (
        state_dir
        / "instances"
        / f"{instance}.json"
    )


def command_doctor(args):
    image = validate_image(
        Path(args.image)
    )

    compat = compatibility_check(
        Path(args.image),
        args.runtime_image,
    )

    license_status = inspect_license(
        Path(args.license_file)
    )

    result = {
        "provider":
            "iol",

        "status":
            "ready-for-provider"
            if compat["status"] == "pass"
            else "blocked",

        "image":
            image,

        "compatibility":
            compat,

        "license":
            license_status,

        "startup_allowed":
            False,

        "startup_reason":
            (
                "Startup ainda nao foi "
                "implementado nesta etapa."
            ),
    }

    print(
        json.dumps(
            result,
            indent=2,
        )
    )


def command_license_status(
    args,
):
    result = inspect_license(
        Path(args.license_file)
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    if not result[
        "configured"
    ]:
        return 3

    return 0


def command_prepare(
    args,
):
    instance = validate_instance_name(
        args.instance
    )

    image = validate_image(
        Path(args.image)
    )

    compatibility_check(
        Path(args.image),
        args.runtime_image,
    )

    state_dir = Path(
        args.state_dir
    ).resolve()

    instances = ensure_state_dirs(
        state_dir
    )

    path = (
        instances
        / f"{instance}.json"
    )

    if path.exists():
        fail(
            f"Instancia ja preparada: {instance}"
        )

    manifest = {
        "schema_version":
            1,

        "provider":
            "iol",

        "instance":
            instance,

        "state":
            "prepared",

        "image":
            image,

        "runtime_image":
            args.runtime_image,

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "license_gate": {
            "path":
                args.license_file,

            "required_for_start":
                True,
        },

        "network": {
            "status":
                "not-configured",
        },

        "console": {
            "status":
                "not-configured",
        },
    }

    temp_fd, temp_name = tempfile.mkstemp(
        prefix=instance + ".",
        suffix=".tmp",
        dir=str(instances),
    )

    try:
        with os.fdopen(
            temp_fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                manifest,
                handle,
                indent=2,
            )

            handle.write(
                "\n"
            )

        os.chmod(
            temp_name,
            0o644,
        )

        os.replace(
            temp_name,
            path,
        )

    finally:
        if os.path.exists(
            temp_name
        ):
            os.unlink(
                temp_name
            )

    print(
        json.dumps(
            manifest,
            indent=2,
        )
    )


def command_list(args):
    state_dir = Path(
        args.state_dir
    ).resolve()

    instances = (
        state_dir
        / "instances"
    )

    result = []

    if instances.is_dir():
        for path in sorted(
            instances.glob(
                "ulab-iol-*.json"
            )
        ):
            try:
                data = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )

            except (
                OSError,
                json.JSONDecodeError,
            ):
                continue

            result.append(
                {
                    "instance":
                        data.get(
                            "instance"
                        ),

                    "state":
                        data.get(
                            "state"
                        ),

                    "provider":
                        data.get(
                            "provider"
                        ),
                }
            )

    print(
        json.dumps(
            {
                "instances":
                    result,
            },
            indent=2,
        )
    )


def command_inspect(args):
    instance = validate_instance_name(
        args.instance
    )

    path = manifest_path(
        Path(
            args.state_dir
        ).resolve(),
        instance,
    )

    if not path.is_file():
        fail(
            f"Instancia nao encontrada: {instance}"
        )

    print(
        path.read_text(
            encoding="utf-8"
        ),
        end="",
    )


def command_remove_prepared(args):
    instance = validate_instance_name(
        args.instance
    )

    path = manifest_path(
        Path(
            args.state_dir
        ).resolve(),
        instance,
    )

    if not path.is_file():
        fail(
            f"Instancia nao encontrada: {instance}"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if data.get(
        "state"
    ) != "prepared":
        fail(
            "Somente instancia no estado "
            "prepared pode ser removida "
            "por este comando."
        )

    path.unlink()

    print(
        json.dumps(
            {
                "status":
                    "removed",

                "instance":
                    instance,

                "runtime_process_touched":
                    False,
            },
            indent=2,
        )
    )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="unidac-lab-iolctl"
    )

    parser.add_argument(
        "--runtime-image",
        default=DEFAULT_RUNTIME_IMAGE,
    )

    parser.add_argument(
        "--license-file",
        default=str(
            DEFAULT_LICENSE_FILE
        ),
    )

    parser.add_argument(
        "--state-dir",
        default=str(
            DEFAULT_STATE_DIR
        ),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    doctor = sub.add_parser(
        "doctor"
    )

    doctor.add_argument(
        "--image",
        required=True,
    )

    doctor.set_defaults(
        func=command_doctor
    )

    license_status = sub.add_parser(
        "license-status"
    )

    license_status.set_defaults(
        func=command_license_status
    )

    prepare = sub.add_parser(
        "prepare"
    )

    prepare.add_argument(
        "--instance",
        required=True,
    )

    prepare.add_argument(
        "--image",
        required=True,
    )

    prepare.set_defaults(
        func=command_prepare
    )

    list_command = sub.add_parser(
        "list"
    )

    list_command.set_defaults(
        func=command_list
    )

    inspect = sub.add_parser(
        "inspect"
    )

    inspect.add_argument(
        "--instance",
        required=True,
    )

    inspect.set_defaults(
        func=command_inspect
    )

    remove = sub.add_parser(
        "remove-prepared"
    )

    remove.add_argument(
        "--instance",
        required=True,
    )

    remove.set_defaults(
        func=command_remove_prepared
    )

    return parser


def main():
    parser = build_parser()

    args = parser.parse_args()

    try:
        result = args.func(
            args
        )

        if isinstance(
            result,
            int,
        ):
            return result

        return 0

    except IolError as error:
        print(
            json.dumps(
                {
                    "status":
                        "error",

                    "message":
                        str(error),
                },
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
