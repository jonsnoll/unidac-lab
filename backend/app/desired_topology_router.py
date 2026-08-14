from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.desired_topology_service import (
    get_desired_topology,
    save_desired_topology,
)


router = APIRouter(
    prefix="/api/lab/desired",
    tags=["desired-topology"],
)


class DesiredNode(BaseModel):
    id: str
    template_id: str
    name: str
    state: str = "planned"
    properties: dict[str, Any] = Field(
        default_factory=dict
    )


class DesiredLink(BaseModel):
    id: str
    source: str
    target: str
    source_port: str | None = None
    target_port: str | None = None
    properties: dict[str, Any] = Field(
        default_factory=dict
    )


class DesiredTopology(BaseModel):
    schema_version: int = 1
    nodes: list[DesiredNode] = Field(
        default_factory=list
    )
    links: list[DesiredLink] = Field(
        default_factory=list
    )


@router.get("")
def read_desired_topology():
    return get_desired_topology()


@router.put("")
def update_desired_topology(
    topology: DesiredTopology,
):
    return save_desired_topology(
        topology.model_dump()
    )
