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


def run_agent(
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
