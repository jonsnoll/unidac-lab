#!/usr/bin/env python3

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
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

DEFAULT_DAEMON = Path(
    "/usr/local/libexec/unidac-lab-iold"
)

DEFAULT_UBRIDGE = Path(
    "/usr/local/bin/ubridge"
)

DEFAULT_COMPAT_LIB = Path(
    "/opt/unidac-lab/iol-compat/lib"
)

INSTANCE_RE = re.compile(
    r"^ulab-iol-[a-z0-9][a-z0-9-]{0,47}$"
)

PORT_BINDING_RE = re.compile(
    r"^(port[1-9][0-9]?)=([A-Za-z0-9_.:-]{1,64})$"
)


class IolError(RuntimeError):
    pass


def fail(message):
    raise IolError(
        message
    )


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

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


def private_compat_check(
    image,
):
    if not DEFAULT_COMPAT_LIB.is_dir():
        fail(
            "Private compatibility directory "
            "nao instalado."
        )

    process = subprocess.run(
        [
            "ldd",
            str(
                image.resolve()
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={
            **os.environ,
            "LD_LIBRARY_PATH":
                str(
                    DEFAULT_COMPAT_LIB
                ),
        },
    )

    output = (
        process.stdout
        + process.stderr
    )

    if (
        process.returncode != 0
        or
        "not found" in output
    ):
        fail(
            "Private compatibility check "
            "falhou:\n"
            + output
        )

    if (
        str(
            DEFAULT_COMPAT_LIB
            / "libcrypto.so.4"
        )
        not in output
    ):
        fail(
            "libcrypto.so.4 nao foi resolvida "
            "pelo private compat dir."
        )

    return {
        "status":
            "pass",

        "ld_library_path":
            str(
                DEFAULT_COMPAT_LIB
            ),

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

    work = (
        state_dir
        / "work"
    )

    instances.mkdir(
        parents=True,
        exist_ok=True,
    )

    work.mkdir(
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

    os.chmod(
        work,
        0o755,
    )

    return (
        instances,
        work,
    )


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


def load_manifest(
    state_dir,
    instance,
):
    path = manifest_path(
        state_dir,
        instance,
    )

    if not path.is_file():
        fail(
            f"Instancia nao encontrada: {instance}"
        )

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as error:
        fail(
            "Manifest invalido: "
            + str(
                error
            )
        )


def save_manifest(
    state_dir,
    instance,
    data,
):
    path = manifest_path(
        state_dir,
        instance,
    )

    temp = path.with_suffix(
        ".json.tmp"
    )

    temp.write_text(
        json.dumps(
            data,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    os.chmod(
        temp,
        0o644,
    )

    os.replace(
        temp,
        path,
    )


def port_available(
    port,
):
    for sock_type in (
        socket.SOCK_STREAM,
        socket.SOCK_DGRAM,
    ):
        sock = socket.socket(
            socket.AF_INET,
            sock_type,
        )

        try:
            sock.bind(
                (
                    "127.0.0.1",
                    port,
                )
            )

        except OSError:
            sock.close()

            return False

        sock.close()

    return True


def used_application_ids(
    state_dir,
):
    result = set()

    instances = (
        state_dir
        / "instances"
    )

    if not instances.is_dir():
        return result

    for path in instances.glob(
        "ulab-iol-*.json"
    ):
        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            continue

        value = data.get(
            "application_id"
        )

        if isinstance(
            value,
            int,
        ):
            result.add(
                value
            )

    return result


def allocate_application_id(
    state_dir,
):
    used = used_application_ids(
        state_dir
    )

    for application_id in range(
        1,
        101,
    ):
        if application_id in used:
            continue

        ubridge_port = (
            45000
            + application_id
        )

        console_port = (
            50000
            + application_id
        )

        udp_base = (
            30000
            + (
                application_id
                * 64
            )
        )

        if (
            udp_base
            + 31
            > 65535
        ):
            continue

        if not port_available(
            ubridge_port
        ):
            continue

        if not port_available(
            console_port
        ):
            continue

        return application_id

    fail(
        "Nao existe application_id livre "
        "no pool local."
    )


def parse_bindings(
    values,
    ethernet_ports,
):
    bindings = []

    seen_ports = set()

    for value in values:
        match = PORT_BINDING_RE.fullmatch(
            value
        )

        if not match:
            fail(
                "Binding invalido. "
                "Formato: portN=linux-bridge"
            )

        port_name = match.group(
            1
        )

        bridge = match.group(
            2
        )

        index = int(
            port_name[4:]
        )

        if index > ethernet_ports:
            fail(
                f"{port_name} excede "
                f"{ethernet_ports} portas."
            )

        if port_name in seen_ports:
            fail(
                "Binding duplicado: "
                + port_name
            )

        if not Path(
            "/sys/class/net"
        ).joinpath(
            bridge
        ).exists():
            fail(
                "Interface/bridge Linux "
                f"nao existe: {bridge}"
            )

        bridge_marker = (
            Path(
                "/sys/class/net"
            )
            / bridge
            / "bridge"
        )

        if not bridge_marker.exists():
            fail(
                "Destino nao e Linux bridge: "
                + bridge
            )

        seen_ports.add(
            port_name
        )

        bindings.append(
            {
                "port":
                    port_name,

                "bridge":
                    bridge,
            }
        )

    return bindings


def enrich_udp_bindings(
    application_id,
    bindings,
):
    udp_base = (
        30000
        + (
            application_id
            * 64
        )
    )

    result = []

    for item in bindings:
        index = (
            int(
                item[
                    "port"
                ][4:]
            )
            - 1
        )

        local_port = (
            udp_base
            + (
                index
                * 2
            )
        )

        remote_port = (
            local_port
            + 1
        )

        result.append(
            {
                **item,

                "udp_local":
                    local_port,

                "udp_remote":
                    remote_port,
            }
        )

    return result


def write_netmap(
    path,
    application_id,
):
    bridge_id = (
        application_id
        + 512
    )

    lines = []

    for bay in range(
        0,
        16,
    ):
        for unit in range(
            0,
            4,
        ):
            lines.append(
                (
                    f"{bridge_id}:"
                    f"{bay}/{unit}"
                    f"{application_id:>5d}:"
                    f"{bay}/{unit}"
                )
            )

    path.write_text(
        "\n".join(
            lines
        )
        + "\n",
        encoding="utf-8",
    )

    return lines


def runtime_command(
    manifest,
):
    command = [
        "iou.bin",
        "-e",
        str(
            manifest[
                "ethernet_adapters"
            ]
        ),
        "-s",
        "0",
        "-n",
        str(
            manifest[
                "nvram_kb"
            ]
        ),
        "-m",
        str(
            manifest[
                "memory_mb"
            ]
        ),
    ]

    if not manifest.get(
        "network_bindings",
        []
    ):
        command.append(
            "-N"
        )

    command.append(
        str(
            manifest[
                "application_id"
            ]
        )
    )

    return command


def daemon_pid_path(
    instance,
):
    return (
        Path(
            "/run/unidac-lab/iol"
        )
        / f"{instance}.pid"
    )


def process_alive(
    pid,
):
    try:
        os.kill(
            pid,
            0,
        )

    except OSError:
        return False

    return True


def command_doctor(
    args,
):
    image = validate_image(
        Path(
            args.image
        )
    )

    compat = compatibility_check(
        Path(
            args.image
        ),
        args.runtime_image,
    )

    private = private_compat_check(
        Path(
            args.image
        )
    )

    license_status = inspect_license(
        Path(
            args.license_file
        )
    )

    ubridge = {
        "installed":
            DEFAULT_UBRIDGE.is_file(),

        "path":
            str(
                DEFAULT_UBRIDGE
            ),
    }

    if not ubridge[
        "installed"
    ]:
        fail(
            "uBridge nao instalado."
        )

    daemon = {
        "installed":
            DEFAULT_DAEMON.is_file(),

        "path":
            str(
                DEFAULT_DAEMON
            ),
    }

    result = {
        "provider":
            "iol",

        "status":
            "runtime-plumbing-ready",

        "image":
            image,

        "sandbox_compatibility":
            compat,

        "private_compatibility":
            private,

        "ubridge":
            ubridge,

        "daemon":
            daemon,

        "license":
            license_status,

        "startup_allowed":
            license_status[
                "configured"
            ],

        "startup_note":
            (
                "Start somente com iourc "
                "fornecido e autorizado "
                "pelo usuario."
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
        Path(
            args.license_file
        )
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


def command_install_license(
    args,
):
    if not args.acknowledge_authorized:
        fail(
            "Instalacao bloqueada. "
            "Use --acknowledge-authorized "
            "somente para um iourc que voce "
            "tem autorizacao para utilizar."
        )

    source = Path(
        args.source
    ).resolve()

    if not source.is_file():
        fail(
            f"Arquivo nao encontrado: {source}"
        )

    if source.stat().st_size <= 0:
        fail(
            "Arquivo de licenca esta vazio."
        )

    destination = Path(
        args.license_file
    ).resolve()

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copyfile(
        source,
        destination,
    )

    os.chown(
        destination,
        0,
        0,
    )

    os.chmod(
        destination,
        0o600,
    )

    print(
        json.dumps(
            {
                "status":
                    "installed",

                "path":
                    str(
                        destination
                    ),

                "authorization_acknowledged":
                    True,

                "contents_logged":
                    False,
            },
            indent=2,
        )
    )


def command_prepare(
    args,
):
    instance = validate_instance_name(
        args.instance
    )

    image = validate_image(
        Path(
            args.image
        )
    )

    compatibility_check(
        Path(
            args.image
        ),
        args.runtime_image,
    )

    private_compat_check(
        Path(
            args.image
        )
    )

    state_dir = Path(
        args.state_dir
    ).resolve()

    instances, work = (
        ensure_state_dirs(
            state_dir
        )
    )

    path = (
        instances
        / f"{instance}.json"
    )

    if path.exists():
        fail(
            f"Instancia ja preparada: {instance}"
        )

    ethernet_ports = int(
        args.ethernet_ports
    )

    if (
        ethernet_ports < 4
        or ethernet_ports > 64
    ):
        fail(
            "ethernet-ports deve estar "
            "entre 4 e 64."
        )

    ethernet_adapters = int(
        math.ceil(
            ethernet_ports
            / 4
        )
    )

    application_id = (
        allocate_application_id(
            state_dir
        )
    )

    bindings = parse_bindings(
        args.bridge,
        ethernet_ports,
    )

    bindings = enrich_udp_bindings(
        application_id,
        bindings,
    )

    work_path = (
        work
        / instance
    )

    work_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    netmap_path = (
        work_path
        / "NETMAP"
    )

    netmap_lines = write_netmap(
        netmap_path,
        application_id,
    )

    manifest = {
        "schema_version":
            2,

        "provider":
            "iol",

        "instance":
            instance,

        "state":
            "prepared",

        "application_id":
            application_id,

        "image":
            image,

        "runtime_image":
            args.runtime_image,

        "ethernet_ports":
            ethernet_ports,

        "ethernet_adapters":
            ethernet_adapters,

        "serial_adapters":
            0,

        "memory_mb":
            int(
                args.memory_mb
            ),

        "nvram_kb":
            int(
                args.nvram_kb
            ),

        "network_bindings":
            bindings,

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

        "runtime": {
            "work_dir":
                str(
                    work_path
                ),

            "netmap":
                str(
                    netmap_path
                ),

            "netmap_lines":
                len(
                    netmap_lines
                ),

            "ubridge_control_port":
                45000
                + application_id,

            "console_host":
                "127.0.0.1",

            "console_port":
                50000
                + application_id,

            "private_compat_lib":
                str(
                    DEFAULT_COMPAT_LIB
                ),
        },
    }

    save_manifest(
        state_dir,
        instance,
        manifest,
    )

    print(
        json.dumps(
            manifest,
            indent=2,
        )
    )


def command_start_plan(
    args,
):
    instance = validate_instance_name(
        args.instance
    )

    state_dir = Path(
        args.state_dir
    ).resolve()

    manifest = load_manifest(
        state_dir,
        instance,
    )

    license_status = inspect_license(
        Path(
            manifest[
                "license_gate"
            ][
                "path"
            ]
        )
    )

    bindings = []

    for item in manifest.get(
        "network_bindings",
        []
    ):
        port_index = (
            int(
                item[
                    "port"
                ][4:]
            )
            - 1
        )

        bindings.append(
            {
                **item,

                "bay":
                    port_index
                    // 4,

                "unit":
                    port_index
                    % 4,
            }
        )

    result = {
        "instance":
            instance,

        "application_id":
            manifest[
                "application_id"
            ],

        "command":
            runtime_command(
                manifest
            ),

        "environment": {
            "LD_LIBRARY_PATH":
                str(
                    DEFAULT_COMPAT_LIB
                ),

            "IOURC":
                manifest[
                    "license_gate"
                ][
                    "path"
                ],
        },

        "ubridge": {
            "bridge_id":
                manifest[
                    "application_id"
                ]
                + 512,

            "control_port":
                manifest[
                    "runtime"
                ][
                    "ubridge_control_port"
                ],
        },

        "console": {
            "host":
                manifest[
                    "runtime"
                ][
                    "console_host"
                ],

            "port":
                manifest[
                    "runtime"
                ][
                    "console_port"
                ],
        },

        "network_bindings":
            bindings,

        "license":
            license_status,

        "would_execute_ios":
            False,

        "start_allowed":
            license_status[
                "configured"
            ],

        "note":
            (
                "Este comando e apenas "
                "um plano. Nenhum processo "
                "Cisco foi iniciado."
            ),
    }

    print(
        json.dumps(
            result,
            indent=2,
        )
    )


def command_list(
    args,
):
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

            except Exception:
                continue

            pid_path = daemon_pid_path(
                data.get(
                    "instance",
                    "",
                )
            )

            running = False

            if pid_path.is_file():
                try:
                    pid = int(
                        pid_path.read_text(
                            encoding="utf-8"
                        ).strip()
                    )

                    running = process_alive(
                        pid
                    )

                except Exception:
                    running = False

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

                    "application_id":
                        data.get(
                            "application_id"
                        ),

                    "running":
                        running,

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


def command_inspect(
    args,
):
    instance = validate_instance_name(
        args.instance
    )

    data = load_manifest(
        Path(
            args.state_dir
        ).resolve(),
        instance,
    )

    print(
        json.dumps(
            data,
            indent=2,
        )
    )


def command_status(
    args,
):
    instance = validate_instance_name(
        args.instance
    )

    state_dir = Path(
        args.state_dir
    ).resolve()

    manifest = load_manifest(
        state_dir,
        instance,
    )

    pid_path = daemon_pid_path(
        instance
    )

    daemon_pid = None
    running = False

    if pid_path.is_file():
        try:
            daemon_pid = int(
                pid_path.read_text(
                    encoding="utf-8"
                ).strip()
            )

            running = process_alive(
                daemon_pid
            )

        except Exception:
            running = False

    print(
        json.dumps(
            {
                "instance":
                    instance,

                "manifest_state":
                    manifest.get(
                        "state"
                    ),

                "running":
                    running,

                "daemon_pid":
                    daemon_pid,

                "console":
                    {
                        "host":
                            manifest[
                                "runtime"
                            ][
                                "console_host"
                            ],

                        "port":
                            manifest[
                                "runtime"
                            ][
                                "console_port"
                            ],
                    },
            },
            indent=2,
        )
    )


def command_start(
    args,
):
    instance = validate_instance_name(
        args.instance
    )

    state_dir = Path(
        args.state_dir
    ).resolve()

    manifest = load_manifest(
        state_dir,
        instance,
    )

    license_status = inspect_license(
        Path(
            manifest[
                "license_gate"
            ][
                "path"
            ]
        )
    )

    if manifest.get(
        "network_bindings",
        []
    ):
        fail(
            "Dataplane IOL conectado esta "
            "temporariamente bloqueado. "
            "Use uma instancia sem bindings "
            "para o first-boot core."
        )

    if not license_status[
        "configured"
    ]:
        fail(
            "Startup bloqueado pelo license gate. "
            "Configure um iourc que voce tenha "
            "autorizacao para utilizar."
        )

    pid_path = daemon_pid_path(
        instance
    )

    if pid_path.is_file():
        try:
            pid = int(
                pid_path.read_text(
                    encoding="utf-8"
                ).strip()
            )

            if process_alive(
                pid
            ):
                fail(
                    "Instancia ja esta running."
                )

        except ValueError:
            pass

    work = Path(
        manifest[
            "runtime"
        ][
            "work_dir"
        ]
    )

    work.mkdir(
        parents=True,
        exist_ok=True,
    )

    log = open(
        work
        / "daemon.log",
        "ab",
        buffering=0,
    )

    process = subprocess.Popen(
        [
            str(
                DEFAULT_DAEMON
            ),
            instance,
        ],
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
        env={
            **os.environ,
            "PYTHONUNBUFFERED": "1",
        },
    )

    deadline = (
        time.monotonic()
        + 15
    )

    while (
        time.monotonic()
        < deadline
    ):
        if pid_path.is_file():
            status = load_manifest(
                state_dir,
                instance,
            )

            if status.get(
                "state"
            ) == "running":
                print(
                    json.dumps(
                        {
                            "status":
                                "started",

                            "instance":
                                instance,

                            "daemon_pid":
                                process.pid,

                            "console":
                                {
                                    "host":
                                        status[
                                            "runtime"
                                        ][
                                            "console_host"
                                        ],

                                    "port":
                                        status[
                                            "runtime"
                                        ][
                                            "console_port"
                                        ],
                                },
                        },
                        indent=2,
                    )
                )

                return

        if process.poll() is not None:
            break

        time.sleep(
            0.25
        )

    fail(
        "Daemon IOL nao entrou em running. "
        f"Consulte {work / 'daemon.log'}"
    )


def command_stop(
    args,
):
    instance = validate_instance_name(
        args.instance
    )

    pid_path = daemon_pid_path(
        instance
    )

    if not pid_path.is_file():
        print(
            json.dumps(
                {
                    "status":
                        "already-stopped",

                    "instance":
                        instance,
                },
                indent=2,
            )
        )

        return

    try:
        pid = int(
            pid_path.read_text(
                encoding="utf-8"
            ).strip()
        )

    except ValueError:
        fail(
            "PID file invalido."
        )

    if not process_alive(
        pid
    ):
        try:
            pid_path.unlink()

        except FileNotFoundError:
            pass

        print(
            json.dumps(
                {
                    "status":
                        "stale-pid-cleaned",

                    "instance":
                        instance,
                },
                indent=2,
            )
        )

        return

    os.kill(
        pid,
        signal.SIGTERM,
    )

    deadline = (
        time.monotonic()
        + 10
    )

    while (
        time.monotonic()
        < deadline
    ):
        if not process_alive(
            pid
        ):
            break

        time.sleep(
            0.25
        )

    if process_alive(
        pid
    ):
        fail(
            "Daemon nao encerrou no timeout."
        )

    print(
        json.dumps(
            {
                "status":
                    "stopped",

                "instance":
                    instance,
            },
            indent=2,
        )
    )


def command_remove_prepared(
    args,
):
    instance = validate_instance_name(
        args.instance
    )

    state_dir = Path(
        args.state_dir
    ).resolve()

    path = manifest_path(
        state_dir,
        instance,
    )

    if not path.is_file():
        fail(
            f"Instancia nao encontrada: {instance}"
        )

    data = load_manifest(
        state_dir,
        instance,
    )

    pid_path = daemon_pid_path(
        instance
    )

    if pid_path.is_file():
        fail(
            "Instancia possui daemon ativo/stale. "
            "Execute stop/status antes."
        )

    if data.get(
        "state"
    ) not in {
        "prepared",
        "stopped",
    }:
        fail(
            "Estado nao permite remocao."
        )

    path.unlink()

    work = (
        state_dir
        / "work"
        / instance
    )

    if work.is_dir():
        shutil.rmtree(
            work
        )

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


def command_ubridge_self_test(
    args,
):
    if not DEFAULT_UBRIDGE.is_file():
        fail(
            "uBridge nao instalado."
        )

    port = 45678

    if not port_available(
        port
    ):
        fail(
            "Porta 45678 ocupada."
        )

    temp = Path(
        tempfile.mkdtemp(
            prefix="unidac-ubridge-"
        )
    )

    log_path = (
        temp
        / "ubridge.log"
    )

    log = open(
        log_path,
        "wb",
    )

    process = subprocess.Popen(
        [
            str(
                DEFAULT_UBRIDGE
            ),
            "-H",
            f"127.0.0.1:{port}",
        ],
        cwd=temp,
        stdout=log,
        stderr=subprocess.STDOUT,
    )

    try:
        deadline = (
            time.monotonic()
            + 10
        )

        while (
            time.monotonic()
            < deadline
        ):
            try:
                with socket.create_connection(
                    (
                        "127.0.0.1",
                        port,
                    ),
                    timeout=1,
                ):
                    break

            except OSError:
                time.sleep(
                    0.1
                )

        else:
            fail(
                "uBridge hypervisor nao abriu."
            )

        def send(command):
            with socket.create_connection(
                (
                    "127.0.0.1",
                    port,
                ),
                timeout=3,
            ) as sock:
                sock.sendall(
                    (
                        command
                        + "\n"
                    ).encode(
                        "utf-8"
                    )
                )

                sock.settimeout(
                    3
                )

                data = b""

                while True:
                    chunk = sock.recv(
                        4096
                    )

                    if not chunk:
                        break

                    data += chunk

                    lines = data.decode(
                        "utf-8",
                        errors="replace",
                    ).splitlines()

                    if any(
                        line.startswith(
                            "100-"
                        )
                        for line in lines
                    ):
                        break

                return data.decode(
                    "utf-8",
                    errors="replace",
                )

        modules = send(
            "hypervisor module_list"
        )

        if "iol_bridge" not in modules:
            fail(
                "Modulo iol_bridge ausente."
            )

        create = send(
            "iol_bridge create "
            "ULAB-SELFTEST 999"
        )

        if "100-" not in create:
            fail(
                "iol_bridge create falhou."
            )

        delete = send(
            "iol_bridge delete "
            "ULAB-SELFTEST"
        )

        if "100-" not in delete:
            fail(
                "iol_bridge delete falhou."
            )

        print(
            json.dumps(
                {
                    "status":
                        "pass",

                    "module":
                        "iol_bridge",

                    "ios_started":
                        False,
                },
                indent=2,
            )
        )

    finally:
        process.terminate()

        try:
            process.wait(
                timeout=3
            )

        except subprocess.TimeoutExpired:
            process.kill()

            process.wait()

        log.close()

        shutil.rmtree(
            temp,
            ignore_errors=True,
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

    install_license = sub.add_parser(
        "install-license"
    )

    install_license.add_argument(
        "--source",
        required=True,
    )

    install_license.add_argument(
        "--acknowledge-authorized",
        action="store_true",
    )

    install_license.set_defaults(
        func=command_install_license
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

    prepare.add_argument(
        "--ethernet-ports",
        type=int,
        default=8,
    )

    prepare.add_argument(
        "--memory-mb",
        type=int,
        default=256,
    )

    prepare.add_argument(
        "--nvram-kb",
        type=int,
        default=256,
    )

    prepare.add_argument(
        "--bridge",
        action="append",
        default=[],
        metavar="portN=LINUX_BRIDGE",
    )

    prepare.set_defaults(
        func=command_prepare
    )

    start_plan = sub.add_parser(
        "start-plan"
    )

    start_plan.add_argument(
        "--instance",
        required=True,
    )

    start_plan.set_defaults(
        func=command_start_plan
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

    status = sub.add_parser(
        "status"
    )

    status.add_argument(
        "--instance",
        required=True,
    )

    status.set_defaults(
        func=command_status
    )

    start = sub.add_parser(
        "start"
    )

    start.add_argument(
        "--instance",
        required=True,
    )

    start.set_defaults(
        func=command_start
    )

    stop = sub.add_parser(
        "stop"
    )

    stop.add_argument(
        "--instance",
        required=True,
    )

    stop.set_defaults(
        func=command_stop
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

    self_test = sub.add_parser(
        "ubridge-self-test"
    )

    self_test.set_defaults(
        func=command_ubridge_self_test
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
                        str(
                            error
                        ),
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
