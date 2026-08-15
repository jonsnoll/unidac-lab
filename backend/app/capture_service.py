import re
import socket
import uuid
from pathlib import Path

import dpkt

from app.agent_client import (
    AgentError,
    capture_start,
    capture_status,
    capture_stop,
)
from app.apply_plan_service import (
    build_apply_plan,
)


CAPTURE_ROOT = Path(
    "/var/lib/libvirt/images/"
    "unidac-lab/captures"
)

CAPTURE_ID_RE = re.compile(
    r"^cap-[a-f0-9]{32}$"
)


class CaptureError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        kind="capture-error",
    ):
        super().__init__(message)

        self.kind = kind


def validate_capture_id(
    capture_id,
):
    if not CAPTURE_ID_RE.fullmatch(
        capture_id or ""
    ):
        raise CaptureError(
            "Capture ID invalido.",
            kind="invalid-capture-id",
        )


def resolve_link_target(
    link_id,
):
    plan = build_apply_plan()


    for action in plan.get(
        "actions",
        [],
    ):
        if action.get(
            "action"
        ) not in {
            "create-vm",
            "reuse-vm",
        }:
            continue


        for interface in action.get(
            "interfaces",
            [],
        ):
            if (
                interface.get("link_id")
                != link_id
            ):
                continue


            if not interface.get(
                "connected"
            ):
                raise CaptureError(
                    "Link nao esta conectado.",
                    kind=
                        "link-not-connected",
                )


            if (
                action.get("action")
                == "create-vm"
            ):
                raise CaptureError(
                    "Runtime da VM ainda "
                    "nao existe.",
                    kind=
                        "runtime-not-created",
                )


            return {
                "node_id":
                    action.get(
                        "node_id"
                    ),

                "node_name":
                    action.get(
                        "node_name"
                    ),

                "domain_name":
                    action.get(
                        "domain_name"
                    ),

                "port":
                    interface.get(
                        "port"
                    ),

                "network":
                    interface.get(
                        "network"
                    ),
            }


    raise CaptureError(
        "Link nao possui uma interface "
        "de VM capturavel.",
        kind="link-not-capturable",
    )


def start_link_capture(
    link_id,
):
    target = resolve_link_target(
        link_id
    )


    capture_id = (
        "cap-"
        + uuid.uuid4().hex
    )


    try:
        result = capture_start(
            capture_id,
            target["domain_name"],
            target["port"],
            target["network"],
        )

    except AgentError as error:
        raise CaptureError(
            f"Agent falhou: {error}",
            kind="agent-error",
        ) from error


    return {
        "status":
            "ok",

        "capture_id":
            capture_id,

        "link_id":
            link_id,

        "target":
            target,

        "result":
            result,
    }


def stop_capture(
    capture_id,
):
    validate_capture_id(
        capture_id
    )


    try:
        result = capture_stop(
            capture_id
        )

    except AgentError as error:
        raise CaptureError(
            f"Agent falhou: {error}",
            kind="agent-error",
        ) from error


    return {
        "status":
            "ok",

        "capture_id":
            capture_id,

        "result":
            result,
    }


def get_capture_status(
    capture_id,
):
    validate_capture_id(
        capture_id
    )


    try:
        result = capture_status(
            capture_id
        )

    except AgentError as error:
        raise CaptureError(
            f"Agent falhou: {error}",
            kind="agent-error",
        ) from error


    return {
        "status":
            "ok",

        "capture_id":
            capture_id,

        "result":
            result,
    }



def capture_mac_text(
    value,
):
    if not value:
        return "-"

    return ":".join(
        f"{byte:02x}"
        for byte in value
    )


def capture_ip_text(
    value,
    family,
):
    try:
        return socket.inet_ntop(
            family,
            value,
        )

    except (
        OSError,
        ValueError,
    ):
        return "-"


def capture_tcp_flags(
    flags,
):
    definitions = [
        (
            dpkt.tcp.TH_FIN,
            "FIN",
        ),
        (
            dpkt.tcp.TH_SYN,
            "SYN",
        ),
        (
            dpkt.tcp.TH_RST,
            "RST",
        ),
        (
            dpkt.tcp.TH_PUSH,
            "PSH",
        ),
        (
            dpkt.tcp.TH_ACK,
            "ACK",
        ),
        (
            dpkt.tcp.TH_URG,
            "URG",
        ),
    ]

    active = [
        name
        for bit, name in definitions
        if flags & bit
    ]

    return ",".join(
        active
    )



def capture_l2_summary(
    ethernet,
    raw_packet,
):
    ethernet_type = getattr(
        ethernet,
        "type",
        0,
    )

    payload = (
        raw_packet[14:]
        if len(raw_packet) >= 14
        else b""
    )


    if ethernet_type == 0x88CC:
        return (
            "LLDP",
            "Link Layer Discovery Protocol",
        )


    if ethernet_type == 0x888E:
        return (
            "EAPOL",
            "802.1X authentication",
        )


    if ethernet_type == 0x8809:
        subtype = (
            payload[0]
            if payload
            else None
        )

        labels = {
            1:
                "LACP",

            2:
                "Marker",
        }

        protocol = labels.get(
            subtype,
            "SLOW",
        )

        info = (
            "Slow Protocols"
            if subtype is None
            else
            f"Slow Protocols subtype {subtype}"
        )

        if protocol == "LACP":
            info = (
                "Link Aggregation "
                "Control Protocol"
            )

        elif protocol == "Marker":
            info = (
                "Link Aggregation Marker"
            )

        return (
            protocol,
            info,
        )


    if ethernet_type <= 1500:
        if (
            len(payload) >= 3
            and
            payload[0] == 0x42
            and
            payload[1] == 0x42
            and
            payload[2] in {
                0x03,
                0x00,
            }
        ):
            return (
                "STP",
                "IEEE 802.1D BPDU",
            )


        if (
            len(payload) >= 8
            and
            payload[0:3]
            == b"\xaa\xaa\x03"
        ):
            oui = payload[3:6]
            protocol_id = int.from_bytes(
                payload[6:8],
                "big",
            )

            if (
                oui
                == b"\x00\x00\x0c"
                and
                protocol_id
                == 0x2000
            ):
                return (
                    "CDP",
                    (
                        "Cisco Discovery "
                        "Protocol"
                    ),
                )

            return (
                "SNAP",
                (
                    f"OUI "
                    f"{oui.hex(':')} "
                    f"PID "
                    f"0x{protocol_id:04x}"
                ),
            )


        return (
            "802.3",
            (
                "IEEE 802.3 / LLC "
                f"frame ({ethernet_type} bytes)"
            ),
        )


    return None


def capture_transport_summary(
    payload,
    protocol_number,
    *,
    ipv6=False,
):
    if isinstance(
        payload,
        dpkt.tcp.TCP,
    ):
        flags = capture_tcp_flags(
            payload.flags
        )

        info = (
            f"{payload.sport} -> "
            f"{payload.dport}"
        )

        if flags:
            info += f" [{flags}]"

        if (
            payload.sport == 53
            or
            payload.dport == 53
        ):
            info += " DNS"

        return (
            "TCP",
            info,
        )


    if isinstance(
        payload,
        dpkt.udp.UDP,
    ):
        info = (
            f"{payload.sport} -> "
            f"{payload.dport}"
        )

        if (
            payload.sport == 53
            or
            payload.dport == 53
        ):
            info += " DNS"

        elif {
            payload.sport,
            payload.dport,
        } & {
            67,
            68,
        }:
            info += " DHCP"

        return (
            "UDP",
            info,
        )


    if (
        not ipv6
        and isinstance(
            payload,
            dpkt.icmp.ICMP,
        )
    ):
        labels = {
            0:
                "Echo reply",

            3:
                "Destination unreachable",

            8:
                "Echo request",

            11:
                "Time exceeded",
        }

        description = labels.get(
            payload.type,
            (
                f"type {payload.type} "
                f"code {payload.code}"
            ),
        )

        return (
            "ICMP",
            description,
        )


    if (
        ipv6
        and isinstance(
            payload,
            dpkt.icmp6.ICMP6,
        )
    ):
        labels = {
            1:
                "Destination unreachable",

            3:
                "Time exceeded",

            128:
                "Echo request",

            129:
                "Echo reply",
        }

        description = labels.get(
            payload.type,
            (
                f"type {payload.type} "
                f"code {payload.code}"
            ),
        )

        return (
            "ICMPv6",
            description,
        )


    prefix = (
        "IPv6"
        if ipv6
        else "IPv4"
    )

    return (
        f"{prefix}/{protocol_number}",
        f"IP protocol {protocol_number}",
    )


def capture_packet_summary(
    raw_packet,
):
    length = len(
        raw_packet
    )

    try:
        ethernet = (
            dpkt.ethernet.Ethernet(
                raw_packet
            )
        )

    except (
        dpkt.dpkt.NeedData,
        dpkt.dpkt.UnpackError,
        ValueError,
    ):
        return {
            "source":
                "-",

            "destination":
                "-",

            "protocol":
                "MALFORMED",

            "length":
                length,

            "info":
                "Packet could not be parsed.",
        }


    source_mac = capture_mac_text(
        ethernet.src
    )

    destination_mac = capture_mac_text(
        ethernet.dst
    )

    payload = ethernet.data


    if isinstance(
        payload,
        dpkt.arp.ARP,
    ):
        source_ip = capture_ip_text(
            payload.spa,
            socket.AF_INET,
        )

        destination_ip = (
            capture_ip_text(
                payload.tpa,
                socket.AF_INET,
            )
        )

        if (
            payload.op
            == dpkt.arp.ARP_OP_REQUEST
        ):
            info = (
                f"Who has "
                f"{destination_ip}? "
                f"Tell {source_ip}"
            )

        elif (
            payload.op
            == dpkt.arp.ARP_OP_REPLY
        ):
            info = (
                f"{source_ip} is at "
                f"{source_mac}"
            )

        else:
            info = (
                f"ARP operation "
                f"{payload.op}"
            )

        return {
            "source":
                source_ip,

            "destination":
                destination_ip,

            "protocol":
                "ARP",

            "length":
                length,

            "info":
                info,
        }


    if isinstance(
        payload,
        dpkt.ip.IP,
    ):
        source_ip = capture_ip_text(
            payload.src,
            socket.AF_INET,
        )

        destination_ip = (
            capture_ip_text(
                payload.dst,
                socket.AF_INET,
            )
        )

        protocol, info = (
            capture_transport_summary(
                payload.data,
                payload.p,
                ipv6=False,
            )
        )

        return {
            "source":
                source_ip,

            "destination":
                destination_ip,

            "protocol":
                protocol,

            "length":
                length,

            "info":
                info,
        }


    if isinstance(
        payload,
        dpkt.ip6.IP6,
    ):
        source_ip = capture_ip_text(
            payload.src,
            socket.AF_INET6,
        )

        destination_ip = (
            capture_ip_text(
                payload.dst,
                socket.AF_INET6,
            )
        )

        protocol, info = (
            capture_transport_summary(
                payload.data,
                payload.nxt,
                ipv6=True,
            )
        )

        return {
            "source":
                source_ip,

            "destination":
                destination_ip,

            "protocol":
                protocol,

            "length":
                length,

            "info":
                info,
        }


    ethernet_type = getattr(
        ethernet,
        "type",
        0,
    )

    l2_summary = capture_l2_summary(
        ethernet,
        raw_packet,
    )

    if l2_summary:
        protocol, info = l2_summary

        return {
            "source":
                source_mac,

            "destination":
                destination_mac,

            "protocol":
                protocol,

            "length":
                length,

            "info":
                info,
        }

    return {
        "source":
            source_mac,

        "destination":
            destination_mac,

        "protocol":
            (
                f"ETH/0x"
                f"{ethernet_type:04x}"
            ),

        "length":
            length,

        "info":
            "Ethernet frame",
    }


def get_capture_preview(
    capture_id,
    *,
    limit=100,
):
    validate_capture_id(
        capture_id
    )


    if (
        not isinstance(
            limit,
            int,
        )
        or
        limit < 1
        or
        limit > 500
    ):
        raise CaptureError(
            "Limite de preview invalido.",
            kind=
                "invalid-preview-limit",
        )


    path = get_capture_file(
        capture_id
    )


    packets = []

    first_timestamp = None
    truncated = False


    try:
        with path.open(
            "rb"
        ) as handle:
            reader = dpkt.pcap.Reader(
                handle
            )


            for (
                timestamp,
                raw_packet,
            ) in reader:
                if (
                    first_timestamp
                    is None
                ):
                    first_timestamp = (
                        float(
                            timestamp
                        )
                    )


                if (
                    len(packets)
                    >= limit
                ):
                    truncated = True
                    break


                summary = (
                    capture_packet_summary(
                        raw_packet
                    )
                )

                summary.update(
                    {
                        "number":
                            len(
                                packets
                            )
                            + 1,

                        "time":
                            round(
                                float(
                                    timestamp
                                )
                                -
                                first_timestamp,
                                6,
                            ),
                    }
                )

                packets.append(
                    summary
                )


    except (
        OSError,
        ValueError,
        dpkt.dpkt.NeedData,
        dpkt.dpkt.UnpackError,
    ) as error:
        raise CaptureError(
            (
                "Nao foi possivel "
                "interpretar o PCAP: "
                f"{error}"
            ),
            kind=
                "capture-parse-error",
        ) from error


    return {
        "status":
            "ok",

        "capture_id":
            capture_id,

        "size_bytes":
            path.stat().st_size,

        "limit":
            limit,

        "returned":
            len(
                packets
            ),

        "truncated":
            truncated,

        "packets":
            packets,
    }


def get_capture_file(
    capture_id,
):
    validate_capture_id(
        capture_id
    )

    status = get_capture_status(
        capture_id
    )

    result = status[
        "result"
    ]


    if result.get(
        "running"
    ):
        raise CaptureError(
            "Pare a captura antes "
            "de fazer download.",
            kind="capture-running",
        )


    path = (
        CAPTURE_ROOT /
        f"{capture_id}.pcap"
    )


    if not path.is_file():
        raise CaptureError(
            "Arquivo PCAP nao encontrado.",
            kind="capture-not-found",
        )


    return path
