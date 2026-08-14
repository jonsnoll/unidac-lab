import re
import subprocess


def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout


def get_namespaces():
    output = run_command(["ip", "netns", "list"])

    namespaces = []

    for line in output.splitlines():
        if not line.strip():
            continue

        name = line.split()[0]

        namespaces.append(
            {
                "name": name,
                "state": "present",
            }
        )

    return sorted(namespaces, key=lambda item: item["name"])


def get_bridge_members(bridge_name):
    output = run_command(
        [
            "ip",
            "-o",
            "link",
            "show",
            "master",
            bridge_name,
        ]
    )

    members = []

    for line in output.splitlines():
        if not line.strip():
            continue

        match = re.match(r"^\d+:\s+([^:@]+)", line)

        if not match:
            continue

        interface_name = match.group(1)

        namespace_match = re.search(
            r"link-netns\s+([^\s]+)",
            line,
        )

        namespace = (
            namespace_match.group(1)
            if namespace_match
            else None
        )

        members.append(
            {
                "interface": interface_name,
                "namespace": namespace,
            }
        )

    return members


def get_namespace_links(networks):
    links = []

    for network in networks:
        bridge = network.get("bridge")

        if not bridge or not network.get("active"):
            continue

        try:
            members = get_bridge_members(bridge)
        except subprocess.CalledProcessError:
            continue

        for member in members:
            if not member["namespace"]:
                continue

            links.append(
                {
                    "namespace": member["namespace"],
                    "network": network["name"],
                    "bridge": bridge,
                    "host_interface": member["interface"],
                }
            )

    return sorted(
        links,
        key=lambda item: (
            item["namespace"],
            item["network"],
        ),
    )
