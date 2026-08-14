from fastapi import APIRouter, HTTPException

from app.catalog_service import (
    get_device,
    get_devices,
)


router = APIRouter(
    prefix="/api/catalog",
    tags=["catalog"],
)


@router.get("/devices")
def list_devices():
    devices = get_devices()

    return {
        "count": len(devices),
        "devices": devices,
    }


@router.get("/devices/{device_id}")
def device_details(device_id: str):
    device = get_device(device_id)

    if device is None:
        raise HTTPException(
            status_code=404,
            detail=f"Device nao encontrado: {device_id}",
        )

    return device
