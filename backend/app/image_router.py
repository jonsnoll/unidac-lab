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
