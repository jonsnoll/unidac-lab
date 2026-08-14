from app.libvirt_service import get_domains, get_networks
from app.network_service import get_namespaces, get_namespace_links


def get_topology():
    domains = get_domains()
    networks = get_networks()
    namespaces = get_namespaces()
    namespace_links = get_namespace_links(networks)

    nodes = []
    links = []

    # Redes
    for network in networks:
        nodes.append(
            {
                "id": f'net:{network["name"]}',
                "type": "network",
                "name": network["name"],
                "state": network["state"],
                "bridge": network["bridge"],
            }
        )

    # VMs
    for domain in domains:
        nodes.append(
            {
                "id": f'vm:{domain["name"]}',
                "type": "vm",
                "name": domain["name"],
                "state": domain["state"],
                "active": domain["active"],
            }
        )

        for interface in domain["interfaces"]:
            network_name = interface.get("source")

            if not isinstance(network_name, str):
                continue

            links.append(
                {
                    "id": (
                        f'vm:{domain["name"]}:'
                        f'{interface["guest_port"]}:'
                        f'net:{network_name}'
                    ),
                    "type": "vm-network",
                    "source": f'vm:{domain["name"]}',
                    "source_port": interface["guest_port"],
                    "target": f'net:{network_name}',
                    "details": {
                        "libvirt_target": interface["target"],
                        "mac": interface["mac"],
                        "model": interface["model"],
                    },
                }
            )

    # Hosts Linux / namespaces
    for namespace in namespaces:
        nodes.append(
            {
                "id": f'host:{namespace["name"]}',
                "type": "host",
                "name": namespace["name"],
                "state": namespace["state"],
            }
        )

    for link in namespace_links:
        links.append(
            {
                "id": (
                    f'host:{link["namespace"]}:'
                    f'net:{link["network"]}'
                ),
                "type": "host-network",
                "source": f'host:{link["namespace"]}',
                "target": f'net:{link["network"]}',
                "details": {
                    "bridge": link["bridge"],
                    "host_interface": link["host_interface"],
                },
            }
        )

    nodes.sort(key=lambda item: (item["type"], item["name"]))
    links.sort(key=lambda item: item["id"])

    return {
        "project": "unidac-lab",
        "lab": "vxlan-fgt-01",
        "nodes": nodes,
        "links": links,
    }
