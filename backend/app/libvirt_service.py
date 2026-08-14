import xml.etree.ElementTree as ET

import libvirt


LIBVIRT_URI = "qemu:///system"


DOMAIN_STATES = {
    libvirt.VIR_DOMAIN_NOSTATE: "nostate",
    libvirt.VIR_DOMAIN_RUNNING: "running",
    libvirt.VIR_DOMAIN_BLOCKED: "blocked",
    libvirt.VIR_DOMAIN_PAUSED: "paused",
    libvirt.VIR_DOMAIN_SHUTDOWN: "shutdown",
    libvirt.VIR_DOMAIN_SHUTOFF: "shutoff",
    libvirt.VIR_DOMAIN_CRASHED: "crashed",
    libvirt.VIR_DOMAIN_PMSUSPENDED: "pmsuspended",
}


def get_connection():
    conn = libvirt.openReadOnly(LIBVIRT_URI)

    if conn is None:
        raise RuntimeError("Nao foi possivel conectar ao libvirt")

    return conn


def get_domain_interfaces(domain):
    xml = domain.XMLDesc(0)
    root = ET.fromstring(xml)

    interfaces = []

    for index, interface in enumerate(root.findall("./devices/interface"), start=1):
        interface_type = interface.get("type")

        mac_element = interface.find("mac")
        source_element = interface.find("source")
        target_element = interface.find("target")
        model_element = interface.find("model")

        mac = mac_element.get("address") if mac_element is not None else None
        target = target_element.get("dev") if target_element is not None else None
        model = model_element.get("type") if model_element is not None else None

        source = None

        if source_element is not None:
            if interface_type == "network":
                source = source_element.get("network")
            elif interface_type == "bridge":
                source = source_element.get("bridge")
            else:
                source = dict(source_element.attrib)

        interfaces.append(
            {
                "index": index,
                "guest_port": f"port{index}",
                "type": interface_type,
                "source": source,
                "target": target,
                "mac": mac,
                "model": model,
            }
        )

    return interfaces


def get_domains():
    conn = get_connection()

    try:
        domains = []

        for domain in conn.listAllDomains(0):
            state_code = domain.state()[0]

            domains.append(
                {
                    "name": domain.name(),
                    "state": DOMAIN_STATES.get(state_code, "unknown"),
                    "active": domain.isActive() == 1,
                    "interfaces": get_domain_interfaces(domain),
                }
            )

        return sorted(domains, key=lambda item: item["name"])

    finally:
        conn.close()


def get_networks():
    conn = get_connection()

    try:
        networks = []

        for network in conn.listAllNetworks(0):
            bridge = None

            try:
                bridge = network.bridgeName()
            except libvirt.libvirtError:
                pass

            networks.append(
                {
                    "name": network.name(),
                    "state": "active" if network.isActive() else "inactive",
                    "active": network.isActive() == 1,
                    "persistent": network.isPersistent() == 1,
                    "autostart": network.autostart() == 1,
                    "bridge": bridge,
                }
            )

        return sorted(networks, key=lambda item: item["name"])

    finally:
        conn.close()
