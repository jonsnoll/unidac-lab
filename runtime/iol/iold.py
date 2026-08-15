#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time


STATE_ROOT = Path(
    "/var/lib/unidac-lab/iol"
)

RUN_ROOT = Path(
    "/run/unidac-lab/iol"
)

COMPAT_LIB = Path(
    "/opt/unidac-lab/iol-compat/lib"
)

UBRIDGE = Path(
    "/usr/local/bin/ubridge"
)


class RuntimeErrorIOL(RuntimeError):
    pass


def fail(message):
    raise RuntimeErrorIOL(
        message
    )


def manifest_path(instance):
    return (
        STATE_ROOT
        / "instances"
        / f"{instance}.json"
    )


def work_dir(instance):
    return (
        STATE_ROOT
        / "work"
        / instance
    )


def load_manifest(instance):
    path = manifest_path(
        instance
    )

    if not path.is_file():
        fail(
            f"Manifest nao encontrado: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def save_manifest(
    instance,
    data,
):
    path = manifest_path(
        instance
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


def check_license(path):
    path = Path(
        path
    )

    if not path.is_file():
        fail(
            "License gate bloqueado: "
            "arquivo iourc autorizado "
            "nao configurado."
        )

    stat = path.stat()

    if stat.st_uid != 0:
        fail(
            "iourc deve pertencer a root."
        )

    if (
        stat.st_mode
        & 0o077
    ):
        fail(
            "iourc deve ter permissao 0600 "
            "ou mais restritiva."
        )

    if stat.st_size <= 0:
        fail(
            "iourc esta vazio."
        )


def write_netmap(
    directory,
    application_id,
):
    bridge_id = (
        application_id
        + 512
    )

    path = (
        directory
        / "NETMAP"
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

    os.chmod(
        path,
        0o644,
    )

    return path


async def wait_tcp(
    host,
    port,
    timeout=10,
):
    deadline = (
        time.monotonic()
        + timeout
    )

    while (
        time.monotonic()
        < deadline
    ):
        try:
            reader, writer = (
                await asyncio.open_connection(
                    host,
                    port,
                )
            )

            writer.close()

            await writer.wait_closed()

            return

        except OSError:
            await asyncio.sleep(
                0.1
            )

    fail(
        f"TCP nao abriu em {host}:{port}"
    )


async def ubridge_command(
    host,
    port,
    command,
):
    reader, writer = (
        await asyncio.open_connection(
            host,
            port,
        )
    )

    writer.write(
        (
            command
            + "\n"
        ).encode(
            "utf-8"
        )
    )

    await writer.drain()

    lines = []

    while True:
        raw = await asyncio.wait_for(
            reader.readline(),
            timeout=5,
        )

        if not raw:
            break

        line = raw.decode(
            "utf-8",
            errors="replace",
        ).rstrip()

        lines.append(
            line
        )

        if (
            line.startswith(
                "100-"
            )
            or line.startswith(
                "200-"
            )
            or line.startswith(
                "201-"
            )
            or line.startswith(
                "202-"
            )
            or line.startswith(
                "203-"
            )
            or line.startswith(
                "204-"
            )
            or line.startswith(
                "205-"
            )
            or line.startswith(
                "206-"
            )
            or line.startswith(
                "207-"
            )
            or line.startswith(
                "208-"
            )
            or line.startswith(
                "209-"
            )
        ):
            break

    writer.close()

    await writer.wait_closed()

    if not lines:
        fail(
            "uBridge nao respondeu a: "
            + command
        )

    final = lines[-1]

    if not final.startswith(
        "100-"
    ):
        fail(
            "uBridge rejeitou comando: "
            + command
            + " -> "
            + " | ".join(
                lines
            )
        )

    return lines


def port_to_bay_unit(
    port_name,
):
    if not port_name.startswith(
        "port"
    ):
        fail(
            "Porta IOL invalida: "
            + port_name
        )

    try:
        index = int(
            port_name[4:]
        )

    except ValueError:
        fail(
            "Porta IOL invalida: "
            + port_name
        )

    if (
        index < 1
        or index > 64
    ):
        fail(
            "Porta IOL fora do range: "
            + port_name
        )

    zero = (
        index - 1
    )

    return (
        zero // 4,
        zero % 4,
    )


def tap_name(
    application_id,
    port_name,
):
    port_index = int(
        port_name[4:]
    )

    return (
        f"ui{application_id:03d}"
        f"p{port_index:02d}"
    )


async def ip_command(
    *args,
    check=True,
):
    process = await asyncio.create_subprocess_exec(
        "ip",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    output, _ = (
        await process.communicate()
    )

    text = output.decode(
        "utf-8",
        errors="replace",
    )

    if (
        check
        and
        process.returncode != 0
    ):
        fail(
            "ip command falhou: "
            + " ".join(args)
            + "\n"
            + text
        )

    return (
        process.returncode,
        text,
    )


async def create_tap(
    name,
    bridge,
):
    await ip_command(
        "link",
        "delete",
        name,
        check=False,
    )

    await ip_command(
        "tuntap",
        "add",
        "dev",
        name,
        "mode",
        "tap",
    )

    await ip_command(
        "link",
        "set",
        name,
        "up",
    )

    await ip_command(
        "link",
        "set",
        name,
        "master",
        bridge,
    )


async def delete_tap(
    name,
):
    await ip_command(
        "link",
        "delete",
        name,
        check=False,
    )


class ConsoleHub:
    def __init__(
        self,
        process,
    ):
        self.process = process

        self.clients = set()

        self.reader_task = None

    async def start(
        self,
        host,
        port,
    ):
        server = await asyncio.start_server(
            self.client,
            host,
            port,
        )

        self.reader_task = (
            asyncio.create_task(
                self.pump_output()
            )
        )

        return server

    async def client(
        self,
        reader,
        writer,
    ):
        self.clients.add(
            writer
        )

        try:
            while True:
                data = await reader.read(
                    4096
                )

                if not data:
                    break

                if (
                    self.process.stdin
                    is None
                ):
                    break

                self.process.stdin.write(
                    data
                )

                await self.process.stdin.drain()

        finally:
            self.clients.discard(
                writer
            )

            writer.close()

            try:
                await writer.wait_closed()

            except Exception:
                pass

    async def pump_output(
        self,
    ):
        if (
            self.process.stdout
            is None
        ):
            return

        while True:
            data = await self.process.stdout.read(
                4096
            )

            if not data:
                return

            dead = []

            for writer in self.clients:
                try:
                    writer.write(
                        data
                    )

                    await writer.drain()

                except Exception:
                    dead.append(
                        writer
                    )

            for writer in dead:
                self.clients.discard(
                    writer
                )

                try:
                    writer.close()

                except Exception:
                    pass


async def run_instance(
    instance,
):
    manifest = load_manifest(
        instance
    )

    if manifest.get(
        "state"
    ) not in {
        "prepared",
        "stopped",
    }:
        fail(
            "Estado nao permite start: "
            + str(
                manifest.get(
                    "state"
                )
            )
        )

    license_file = (
        manifest[
            "license_gate"
        ][
            "path"
        ]
    )

    check_license(
        license_file
    )

    if not UBRIDGE.is_file():
        fail(
            "uBridge nao instalado."
        )

    if not COMPAT_LIB.is_dir():
        fail(
            "Private IOL compat lib "
            "nao instalada."
        )

    application_id = int(
        manifest[
            "application_id"
        ]
    )

    directory = work_dir(
        instance
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    os.chmod(
        directory,
        0o755,
    )

    image_source = Path(
        manifest[
            "image"
        ][
            "path"
        ]
    )

    executable = (
        directory
        / "iou.bin"
    )

    shutil.copyfile(
        image_source,
        executable,
    )

    os.chmod(
        executable,
        0o555,
    )

    netmap = write_netmap(
        directory,
        application_id,
    )

    ubridge_port = int(
        manifest[
            "runtime"
        ][
            "ubridge_control_port"
        ]
    )

    console_port = int(
        manifest[
            "runtime"
        ][
            "console_port"
        ]
    )

    ubridge_log = open(
        directory
        / "ubridge.log",
        "ab",
        buffering=0,
    )

    iou_log = open(
        directory
        / "iou.log",
        "ab",
        buffering=0,
    )

    ubridge_process = (
        await asyncio.create_subprocess_exec(
            str(
                UBRIDGE
            ),
            "-H",
            (
                "127.0.0.1:"
                + str(
                    ubridge_port
                )
            ),
            cwd=str(
                directory
            ),
            stdout=ubridge_log,
            stderr=subprocess.STDOUT,
        )
    )

    taps = []

    try:
        await wait_tcp(
            "127.0.0.1",
            ubridge_port,
        )

        bridge_id = (
            application_id
            + 512
        )

        iol_bridge = (
            "IOL-BRIDGE-"
            + str(
                bridge_id
            )
        )

        await ubridge_command(
            "127.0.0.1",
            ubridge_port,
            (
                "iol_bridge create "
                + iol_bridge
                + " "
                + str(
                    bridge_id
                )
            ),
        )

        for binding in manifest.get(
            "network_bindings",
            []
        ):
            port_name = binding[
                "port"
            ]

            linux_bridge = binding[
                "bridge"
            ]

            bay, unit = (
                port_to_bay_unit(
                    port_name
                )
            )

            local_port = int(
                binding[
                    "udp_local"
                ]
            )

            remote_port = int(
                binding[
                    "udp_remote"
                ]
            )

            tap = tap_name(
                application_id,
                port_name,
            )

            await create_tap(
                tap,
                linux_bridge,
            )

            taps.append(
                tap
            )

            await ubridge_command(
                "127.0.0.1",
                ubridge_port,
                (
                    "iol_bridge add_nio_udp "
                    f"{iol_bridge} "
                    f"{application_id} "
                    f"{bay} "
                    f"{unit} "
                    f"{local_port} "
                    "127.0.0.1 "
                    f"{remote_port}"
                ),
            )

            link_bridge = (
                "ULAB-IOL-"
                f"{application_id}-"
                f"{bay}-{unit}"
            )

            await ubridge_command(
                "127.0.0.1",
                ubridge_port,
                (
                    "bridge create "
                    + link_bridge
                ),
            )

            await ubridge_command(
                "127.0.0.1",
                ubridge_port,
                (
                    "bridge add_nio_udp "
                    f"{link_bridge} "
                    f"{remote_port} "
                    "127.0.0.1 "
                    f"{local_port}"
                ),
            )

            await ubridge_command(
                "127.0.0.1",
                ubridge_port,
                (
                    "bridge add_nio_tap "
                    f"{link_bridge} "
                    f"{tap}"
                ),
            )

            await ubridge_command(
                "127.0.0.1",
                ubridge_port,
                (
                    "bridge start "
                    + link_bridge
                ),
            )

        await ubridge_command(
            "127.0.0.1",
            ubridge_port,
            (
                "iol_bridge start "
                + iol_bridge
            ),
        )

        command = [
            str(
                executable
            ),
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
            str(
                application_id
            ),
        ]

        env = os.environ.copy()

        env[
            "LD_LIBRARY_PATH"
        ] = str(
            COMPAT_LIB
        )

        env[
            "IOURC"
        ] = license_file

        iou_process = (
            await asyncio.create_subprocess_exec(
                *command,
                cwd=str(
                    directory
                ),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
            )
        )

        manifest[
            "state"
        ] = "running"

        manifest[
            "runtime"
        ][
            "iou_pid"
        ] = iou_process.pid

        manifest[
            "runtime"
        ][
            "daemon_pid"
        ] = os.getpid()

        manifest[
            "runtime"
        ][
            "netmap"
        ] = str(
            netmap
        )

        save_manifest(
            instance,
            manifest,
        )

        RUN_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        pid_path = (
            RUN_ROOT
            / f"{instance}.pid"
        )

        pid_path.write_text(
            str(
                os.getpid()
            )
            + "\n",
            encoding="utf-8",
        )

        hub = ConsoleHub(
            iou_process
        )

        console_server = (
            await hub.start(
                "127.0.0.1",
                console_port,
            )
        )

        loop = asyncio.get_running_loop()

        stop_event = asyncio.Event()

        def request_stop():
            stop_event.set()

        for sig in (
            signal.SIGTERM,
            signal.SIGINT,
        ):
            loop.add_signal_handler(
                sig,
                request_stop,
            )

        wait_process = (
            asyncio.create_task(
                iou_process.wait()
            )
        )

        wait_stop = (
            asyncio.create_task(
                stop_event.wait()
            )
        )

        done, pending = (
            await asyncio.wait(
                [
                    wait_process,
                    wait_stop,
                ],
                return_when=
                    asyncio.FIRST_COMPLETED,
            )
        )

        for task in pending:
            task.cancel()

        if (
            iou_process.returncode
            is None
        ):
            iou_process.terminate()

            try:
                await asyncio.wait_for(
                    iou_process.wait(),
                    timeout=5,
                )

            except asyncio.TimeoutError:
                iou_process.kill()

                await iou_process.wait()

        console_server.close()

        await console_server.wait_closed()

        manifest[
            "state"
        ] = "stopped"

        manifest[
            "runtime"
        ][
            "last_exit_code"
        ] = iou_process.returncode

        manifest[
            "runtime"
        ].pop(
            "iou_pid",
            None,
        )

        manifest[
            "runtime"
        ].pop(
            "daemon_pid",
            None,
        )

        save_manifest(
            instance,
            manifest,
        )

    finally:
        for tap in taps:
            try:
                await delete_tap(
                    tap
                )

            except Exception:
                pass

        if (
            ubridge_process.returncode
            is None
        ):
            ubridge_process.terminate()

            try:
                await asyncio.wait_for(
                    ubridge_process.wait(),
                    timeout=3,
                )

            except asyncio.TimeoutError:
                ubridge_process.kill()

                await ubridge_process.wait()

        ubridge_log.close()
        iou_log.close()

        pid_path = (
            RUN_ROOT
            / f"{instance}.pid"
        )

        try:
            pid_path.unlink()

        except FileNotFoundError:
            pass


def main():
    parser = argparse.ArgumentParser(
        prog="unidac-lab-iold"
    )

    parser.add_argument(
        "instance"
    )

    args = parser.parse_args()

    try:
        asyncio.run(
            run_instance(
                args.instance
            )
        )

        return 0

    except RuntimeErrorIOL as error:
        print(
            str(error),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
