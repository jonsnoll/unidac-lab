import subprocess

import libvirt
from fastapi import FastAPI, HTTPException


PROJECT_NAME = "unidac-lab"
LAB_NAME = "vxlan-fgt-01"
LIBVIRT_URI = "qemu:///system"


app = FastAPI(
    title="unidac-lab API",
    description="API para gerenciamento e observacao de laboratorios de rede",
    version="0.1.0",
)


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


def get_namespaces():
    result = subprocess.run(
        ["ip", "netns", "list"],
        capture_output=True,
        text=True,
        check=True,
    )

    hosts = []

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        name = line.split()[0]

        hosts.append(
            {
                "name": name,
                "state": "present",
            }
        )

    return hosts


def get_lab_state():
    conn = libvirt.openReadOnly(LIBVIRT_URI)

    if conn is None:
        raise RuntimeError("Nao foi possivel conectar ao libvirt")

    try:
        vms = []

        for domain in conn.listAllDomains(0):
            state_code = domain.state()[0]

            vms.append(
                {
                    "name": domain.name(),
                    "state": DOMAIN_STATES.get(state_code, "unknown"),
                    "active": domain.isActive() == 1,
                }
            )

        networks = []

        for network in conn.listAllNetworks(0):
            networks.append(
                {
                    "name": network.name(),
                    "state": "active" if network.isActive() else "inactive",
                    "active": network.isActive() == 1,
                    "persistent": network.isPersistent() == 1,
                    "autostart": network.autostart() == 1,
                }
            )

        hosts = get_namespaces()

        return {
            "project": PROJECT_NAME,
            "lab": LAB_NAME,
            "vms": sorted(vms, key=lambda item: item["name"]),
            "networks": sorted(networks, key=lambda item: item["name"]),
            "hosts": sorted(hosts, key=lambda item: item["name"]),
        }

    finally:
        conn.close()


@app.get("/")
def root():
    return {
        "project": PROJECT_NAME,
        "status": "online",
        "api_version": "0.1.0",
    }


@app.get("/api/lab/state")
def lab_state():
    try:
        return get_lab_state()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.get("/api/lab/topology")
def lab_topology():
    try:
        from app.topology_service import get_topology

        return get_topology()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


from pydantic import BaseModel

from app.workspace_service import (
    get_layout,
    save_layout,
)


class NodePosition(BaseModel):
    x: float
    y: float


class LayoutNode(BaseModel):
    id: str
    position: NodePosition


class LayoutPayload(BaseModel):
    nodes: list[LayoutNode]


@app.get("/api/lab/layout")
def lab_layout():
    try:
        return get_layout()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.put("/api/lab/layout")
def update_lab_layout(
    layout: LayoutPayload,
):
    try:
        return save_layout(
            layout.model_dump()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


from app.catalog_router import router as catalog_router

app.include_router(catalog_router)
