import json
import subprocess


AGENT_PATH = (
    "/usr/local/libexec/unidac-lab-agent"
)

BASE_COMMAND = [
    "sudo",
    "-n",
    AGENT_PATH,
]


class AgentError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        command=None,
        returncode=None,
        response=None,
    ):
        super().__init__(message)

        self.command = command
        self.returncode = returncode
        self.response = response


def _run_agent_cli(
    command,
    *args,
    input_data=None,
    timeout=120,
):
    argv = [
        *BASE_COMMAND,
        command,
        *[
            str(value)
            for value in args
        ],
    ]


    stdin_text = None

    if input_data is not None:
        stdin_text = json.dumps(
            input_data
        )


    try:
        process = subprocess.run(
            argv,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    except subprocess.TimeoutExpired as error:
        raise AgentError(
            f"Timeout executando Agent: "
            f"{command}",
            command=argv,
        ) from error


    stdout = (
        process.stdout.strip()
    )

    stderr = (
        process.stderr.strip()
    )


    response = None

    if stdout:
        try:
            response = json.loads(
                stdout
            )

        except json.JSONDecodeError as error:
            raise AgentError(
                "Agent retornou resposta "
                "que nao e JSON.",
                command=argv,
                returncode=
                    process.returncode,
                response={
                    "stdout": stdout,
                    "stderr": stderr,
                },
            ) from error


    if process.returncode != 0:
        message = (
            response.get("message")
            if isinstance(
                response,
                dict,
            )
            else None
        )

        raise AgentError(
            message
            or stderr
            or
            f"Agent terminou com "
            f"codigo {process.returncode}.",
            command=argv,
            returncode=
                process.returncode,
            response=response,
        )


    if not isinstance(
        response,
        dict,
    ):
        raise AgentError(
            "Agent nao retornou "
            "objeto JSON.",
            command=argv,
            returncode=
                process.returncode,
            response=response,
        )


    if (
        response.get("status")
        == "error"
    ):
        raise AgentError(
            response.get(
                "message",
                "Agent retornou erro.",
            ),
            command=argv,
            returncode=
                process.returncode,
            response=response,
        )


    return response


def agent_health():
    return run_agent(
        "health"
    )


def ensure_network(
    network_name,
    bridge_name,
):
    return run_agent(
        "network-ensure",
        network_name,
        bridge_name,
    )


def ensure_image(
    vendor,
    image_id,
):
    return run_agent(
        "image-ensure",
        vendor,
        image_id,
        timeout=600,
    )


def ensure_overlay(
    lab_id,
    domain_name,
    vendor,
    image_id,
):
    return run_agent(
        "overlay-ensure",
        lab_id,
        domain_name,
        vendor,
        image_id,
        timeout=300,
    )


def ensure_vm(spec):
    return run_agent(
        "vm-ensure",
        input_data=spec,
        timeout=300,
    )



def vm_start(
    domain_name,
):
    return run_agent(
        "vm-start",
        domain_name,
    )


def vm_shutdown(
    domain_name,
):
    return run_agent(
        "vm-shutdown",
        domain_name,
    )


def vm_restart(
    domain_name,
):
    return run_agent(
        "vm-restart",
        domain_name,
    )


def vm_undefine(
    domain_name,
):
    return run_agent(
        "vm-undefine",
        domain_name,
    )


def capture_start(
    capture_id,
    domain_name,
    port_name,
    network_name,
):
    return run_agent(
        "capture-start",
        capture_id,
        domain_name,
        port_name,
        network_name,
    )


def capture_stop(
    capture_id,
):
    return run_agent(
        "capture-stop",
        capture_id,
    )


def capture_status(
    capture_id,
):
    return run_agent(
        "capture-status",
        capture_id,
    )


def link_netem_set(
    domain_name,
    port_name,
    network_name,
    delay_ms,
    jitter_ms,
    loss_pct,
    rate_mbit,
):
    return run_agent(
        "link-netem-set",
        domain_name,
        port_name,
        network_name,
        delay_ms,
        jitter_ms,
        loss_pct,
        rate_mbit,
    )


def link_netem_clear(
    domain_name,
    port_name,
    network_name,
):
    return run_agent(
        "link-netem-clear",
        domain_name,
        port_name,
        network_name,
    )


def link_netem_status(
    domain_name,
    port_name,
    network_name,
):
    return run_agent(
        "link-netem-status",
        domain_name,
        port_name,
        network_name,
    )


# ===== SOCKET TRANSPORT =====

import json as _agent_json
import os as _agent_os
import socket as _agent_socket


_AGENT_SOCKET = (
    _agent_os.environ.get(
        "UNIDAC_LAB_AGENT_SOCKET",
        "/run/unidac-lab/agent.sock",
    )
)

_AGENT_TRANSPORT = (
    _agent_os.environ.get(
        "UNIDAC_LAB_AGENT_TRANSPORT",
        "auto",
    )
)


class _AgentSocketTransportError(
    RuntimeError
):
    pass


def _agent_socket_exec(
    args,
    stdin_data=None,
):
    request = {
        "mode":
            "exec",

        "argv":
            [
                str(item)
                for item in args
            ],

        "stdin":
            stdin_data,
    }


    client = _agent_socket.socket(
        _agent_socket.AF_UNIX,
        _agent_socket.SOCK_STREAM,
    )

    client.settimeout(
        600
    )


    try:
        try:
            client.connect(
                _AGENT_SOCKET
            )

        except OSError as error:
            raise (
                _AgentSocketTransportError(
                    f"Falha conectando no "
                    f"Agent socket: {error}"
                )
            ) from error


        try:
            client.sendall(
                (
                    _agent_json.dumps(
                        request
                    )
                    + "\n"
                ).encode(
                    "utf-8"
                )
            )

        except OSError as error:
            raise (
                _AgentSocketTransportError(
                    "Falha enviando request "
                    "ao Agent socket."
                )
            ) from error


        data = bytearray()


        while True:
            try:
                chunk = client.recv(
                    65536
                )

            except OSError as error:
                raise (
                    _AgentSocketTransportError(
                        "Falha recebendo resposta "
                        "do Agent socket."
                    )
                ) from error


            if not chunk:
                break

            data.extend(
                chunk
            )


    finally:
        client.close()


    if not data:
        raise _AgentSocketTransportError(
            "Agent socket retornou "
            "resposta vazia."
        )


    try:
        envelope = _agent_json.loads(
            data.decode(
                "utf-8"
            ).strip()
        )

    except (
        UnicodeDecodeError,
        _agent_json.JSONDecodeError,
    ) as error:
        raise _AgentSocketTransportError(
            "Resposta invalida do "
            "Agent socket."
        ) from error


    if not envelope.get(
        "ok"
    ):
        raise AgentError(
            envelope.get(
                "error"
            )
            or
            "Agent daemon rejeitou "
            "a requisicao."
        )


    stdout = envelope.get(
        "stdout",
        "",
    )

    stderr = envelope.get(
        "stderr",
        "",
    )

    returncode = envelope.get(
        "returncode",
        1,
    )


    try:
        result = _agent_json.loads(
            stdout
        )

    except _agent_json.JSONDecodeError:
        result = None


    if returncode != 0:
        message = None

        if isinstance(
            result,
            dict,
        ):
            message = result.get(
                "message"
            )

        raise AgentError(
            message
            or
            stderr.strip()
            or
            stdout.strip()
            or
            f"Agent retornou "
            f"codigo {returncode}"
        )


    if not isinstance(
        result,
        dict,
    ):
        raise AgentError(
            "Agent retornou JSON "
            "invalido."
        )


    if result.get(
        "status"
    ) == "error":
        raise AgentError(
            result.get(
                "message"
            )
            or
            "Agent retornou erro."
        )


    return result


def run_agent(
    *args,
    **kwargs,
):
    stdin_data = None


    if kwargs:
        if len(kwargs) != 1:
            return _run_agent_cli(
                *args,
                **kwargs,
            )


        stdin_data = next(
            iter(
                kwargs.values()
            )
        )


    if (
        stdin_data is not None
        and
        not isinstance(
            stdin_data,
            str,
        )
    ):
        stdin_data = (
            _agent_json.dumps(
                stdin_data
            )
        )


    transport = (
        _agent_os.environ.get(
            "UNIDAC_LAB_AGENT_TRANSPORT",
            _AGENT_TRANSPORT,
        )
    )


    if transport == "cli":
        return _run_agent_cli(
            *args,
            **kwargs,
        )


    try:
        return _agent_socket_exec(
            args,
            stdin_data=
                stdin_data,
        )

    except _AgentSocketTransportError:
        if transport == "socket":
            raise


        return _run_agent_cli(
            *args,
            **kwargs,
        )


def open_console_socket(
    domain_name,
):
    client = _agent_socket.socket(
        _agent_socket.AF_UNIX,
        _agent_socket.SOCK_STREAM,
    )

    client.settimeout(
        15
    )


    try:
        client.connect(
            _AGENT_SOCKET
        )

        request = {
            "mode":
                "console",

            "domain":
                domain_name,
        }

        client.sendall(
            (
                _agent_json.dumps(
                    request
                )
                + "\n"
            ).encode(
                "utf-8"
            )
        )


        header = bytearray()


        while True:
            byte = client.recv(
                1
            )

            if not byte:
                raise AgentError(
                    "Agent daemon encerrou "
                    "o console."
                )

            if byte == b"\n":
                break

            header.extend(
                byte
            )


            if len(header) > 65536:
                raise AgentError(
                    "Header de console "
                    "excedeu limite."
                )


        response = _agent_json.loads(
            header.decode(
                "utf-8"
            )
        )


        if not response.get(
            "ok"
        ):
            raise AgentError(
                response.get(
                    "error"
                )
                or
                "Agent daemon recusou "
                "o console."
            )


        client.settimeout(
            None
        )

        return client


    except Exception:
        client.close()
        raise
