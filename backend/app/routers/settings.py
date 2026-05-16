from fastapi import APIRouter, Depends
from app.deps.auth import verify_api_key
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services.settings_service import get_settings, update_settings

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=SettingsResponse)
def read_settings():
    return get_settings()


@router.patch("/", response_model=SettingsResponse)
def patch_settings(body: SettingsUpdate):
    return update_settings(body)
