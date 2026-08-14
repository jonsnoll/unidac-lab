from fastapi import (
    APIRouter,
    HTTPException,
)

from app.image_service import (
    get_image,
    get_images,
)


router = APIRouter(
    prefix="/api/images",
    tags=["images"],
)


@router.get("")
def list_images(
    template_id: str | None = None,
):
    images = get_images(
        template_id=template_id
    )

    return {
        "count": len(images),
        "images": images,
    }


@router.get("/{image_id}")
def image_details(
    image_id: str,
):
    image = get_image(image_id)

    if image is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Image nao encontrada: "
                f"{image_id}"
            ),
        )

    return image


from fastapi import (
    File,
    Form,
    UploadFile,
)

from app.image_import_service import (
    import_image,
)


@router.post("/import")
def import_image_endpoint(
    image_id: str = Form(...),
    name: str = Form(...),
    vendor: str = Form(...),
    version: str = Form("unknown"),
    template_id: str = Form(...),
    image_format: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        metadata = import_image(
            source_file=file.file,
            image_id=image_id,
            name=name,
            vendor=vendor,
            version=version,
            template_id=template_id,
            image_format=image_format,
        )

        return {
            "status": "imported",
            "image": metadata,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
