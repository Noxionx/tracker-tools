from fastapi import APIRouter

from app.services.storage_service import get_storage_status

router = APIRouter(tags=["storage"])


@router.get("/storage")
async def storage() -> dict[str, object]:
    return get_storage_status()
