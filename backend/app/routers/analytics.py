from datetime import date
from fastapi import APIRouter, Depends, Query
from app.deps.auth import verify_api_key
from app.schemas.analytics import AnalyticsResponse
from app.services.analytics_service import get_analytics

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=AnalyticsResponse)
def analytics(
    start: date = Query(...),
    end: date = Query(...),
):
    return get_analytics(start, end)
