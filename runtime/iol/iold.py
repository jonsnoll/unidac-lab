#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback


STATE_ROOT = Path(
    "/var/lib/unidac-lab/iol"
)

RUN_ROOT = Path(
    "/run/unidac-lab/iol"
)

COMPAT_LIB = Path(
    "/opt/unidac-lab/iol-compat/lib"
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


class ConsoleHub:
    def __init__(
        self,
        process,
        log_handle,
    ):
        self.process = process
        self.log_handle = log_handle
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

            self.log_handle.write(
                data
            )

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

    bindings = manifest.get(
        "network_bindings",
        []
    )

    if bindings:
        fail(
            "Dataplane IOL conectado esta "
            "temporariamente bloqueado. "
            "O first-boot core deve ser "
            "executado sem network bindings."
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

    iou_log = open(
        directory
        / "iou.log",
        "ab",
        buffering=0,
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
        "-N",
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

    iou_process = None
    console_server = None
    hub = None

    try:
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
            "dataplane_mode"
        ] = "disabled-first-boot-core"

        manifest[
            "runtime"
        ][
            "command"
        ] = command

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
            iou_process,
            iou_log,
        )

        console_server = (
            await hub.start(
                "127.0.0.1",
                int(
                    manifest[
                        "runtime"
                    ][
                        "console_port"
                    ]
                ),
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

        if console_server is not None:
            console_server.close()

            await console_server.wait_closed()

        if (
            hub is not None
            and hub.reader_task is not None
        ):
            try:
                await asyncio.wait_for(
                    hub.reader_task,
                    timeout=2,
                )

            except asyncio.TimeoutError:
                hub.reader_task.cancel()

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
            flush=True,
        )

        return 1

    except Exception:
        traceback.print_exc(
            file=sys.stderr
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
