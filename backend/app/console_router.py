import asyncio

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from app.agent_client import (
    AgentError,
    open_console_socket,
)
from app.console_service import (
    ConsoleError,
    ensure_console_ready,
)


router = APIRouter(
    prefix="/api/lab",
    tags=["console"],
)


async def socket_to_websocket(
    websocket,
    agent_socket,
):
    while True:
        try:
            data = await asyncio.to_thread(
                agent_socket.recv,
                4096,
            )

        except OSError:
            return


        if not data:
            return


        await websocket.send_text(
            data.decode(
                "utf-8",
                errors="replace",
            )
        )


async def websocket_to_socket(
    websocket,
    agent_socket,
):
    while True:
        text = (
            await websocket.receive_text()
        )


        await asyncio.to_thread(
            agent_socket.sendall,
            text.encode(
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

    agent_socket = None


    try:
        try:
            runtime = (
                ensure_console_ready(
                    node_id
                )
            )

            agent_socket = (
                await asyncio.to_thread(
                    open_console_socket,
                    runtime[
                        "domain_name"
                    ],
                )
            )

        except (
            ConsoleError,
            AgentError,
            OSError,
        ) as error:
            await websocket.send_text(
                "\r\n"
                "[console error] "
                f"{error}\r\n"
            )

            await websocket.close(
                code=4409
            )

            return


        await websocket.send_text(
            "\r\n"
            "[unidac-lab console/agentd] "
            f"{runtime['domain_name']}"
            "\r\n"
        )


        reader = asyncio.create_task(
            socket_to_websocket(
                websocket,
                agent_socket,
            )
        )

        writer = asyncio.create_task(
            websocket_to_socket(
                websocket,
                agent_socket,
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


    finally:
        if agent_socket is not None:
            try:
                agent_socket.shutdown(
                    2
                )

            except OSError:
                pass

            try:
                agent_socket.close()

            except OSError:
                pass
