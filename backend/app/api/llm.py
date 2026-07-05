from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import AppSettings, get_settings
from app.core.llm import llm_status


router = APIRouter(prefix="/api/llm", tags=["llm"])


class LLMStatusResponse(BaseModel):
    provider: str
    model: str
    base_url: str
    configured: bool


@router.get("/status", response_model=LLMStatusResponse)
def get_llm_status_endpoint(settings: AppSettings = Depends(get_settings)) -> LLMStatusResponse:
    status = llm_status(settings)
    return LLMStatusResponse(
        provider=status.provider,
        model=status.model,
        base_url=status.base_url,
        configured=status.configured,
    )
