import asyncio
import fcntl
import os
import pty
import struct
import subprocess
import termios

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from app.console_service import (
    ConsoleError,
    LIBVIRT_URI,
    VIRSH,
    ensure_console_ready,
)


router = APIRouter(
    prefix="/api/lab",
    tags=["console"],
)


async def read_pty(
    websocket,
    master_fd,
):
    while True:
        try:
            data = await asyncio.to_thread(
                os.read,
                master_fd,
                4096,
            )

        except OSError:
            return


        if not data:
            return


        text = data.decode(
            "utf-8",
            errors="replace",
        )


        await websocket.send_text(
            text
        )


async def write_pty(
    websocket,
    master_fd,
):
    while True:
        message = (
            await websocket.receive_text()
        )

        await asyncio.to_thread(
            os.write,
            master_fd,
            message.encode(
                "utf-8"
            ),
        )


@router.websocket(
    "/nodes/{node_id}/console/ws"
)
async def vm_console(
    websocket: WebSocket,
    node_id: str,
):
    await websocket.accept()


    process = None
    master_fd = None
    slave_fd = None


    try:
        try:
            runtime = (
                ensure_console_ready(
                    node_id
                )
            )

        except ConsoleError as error:
            await websocket.send_text(
                "\r\n"
                "[console error] "
                f"{error}\r\n"
            )

            await websocket.close(
                code=4409
            )

            return


        domain_name = runtime[
            "domain_name"
        ]


        master_fd, slave_fd = (
            pty.openpty()
        )


        window_size = struct.pack(
            "HHHH",
            40,
            120,
            0,
            0,
        )


        fcntl.ioctl(
            master_fd,
            termios.TIOCSWINSZ,
            window_size,
        )


        process = subprocess.Popen(
            [
                VIRSH,
                "-c",
                LIBVIRT_URI,
                "console",
                "--force",
                domain_name,
            ],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
            close_fds=True,
        )


        os.close(
            slave_fd
        )

        slave_fd = None


        await websocket.send_text(
            "\r\n"
            "[unidac-lab console] "
            f"{domain_name}\r\n"
        )


        reader = asyncio.create_task(
            read_pty(
                websocket,
                master_fd,
            )
        )

        writer = asyncio.create_task(
            write_pty(
                websocket,
                master_fd,
            )
        )


        done, pending = (
            await asyncio.wait(
                {
                    reader,
                    writer,
                },
                return_when=
                    asyncio.FIRST_COMPLETED,
            )
        )


        for task in pending:
            task.cancel()


        await asyncio.gather(
            *pending,
            return_exceptions=True,
        )


    except WebSocketDisconnect:
        pass

    except Exception as error:
        try:
            await websocket.send_text(
                "\r\n"
                "[console error] "
                f"{error}\r\n"
            )

        except Exception:
            pass


    finally:
        if slave_fd is not None:
            try:
                os.close(
                    slave_fd
                )

            except OSError:
                pass


        if master_fd is not None:
            try:
                os.close(
                    master_fd
                )

            except OSError:
                pass


        if (
            process is not None
            and
            process.poll() is None
        ):
            process.terminate()

            try:
                process.wait(
                    timeout=2
                )

            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
