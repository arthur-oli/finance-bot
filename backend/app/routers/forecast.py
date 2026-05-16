from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.deps.auth import verify_api_key
from app.schemas.forecast import ForecastResponse
from app.services.forecast_service import get_forecast

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=ForecastResponse)
def forecast(
    year: Optional[int] = Query(None, ge=2020, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
):
    return get_forecast(year, month)
