"""
Agent router: exposes the autonomous farm agent (Muse Spark 1.3 with function calling).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.models import User
from app.services.farm_agent import agent_ask
from app.services.meta_ai import MetaAIUnavailable

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    question: str
    latitude: float = 11.0
    longitude: float = 77.0


class AgentResponse(BaseModel):
    answer: str
    tool_trace: list


@router.post("/ask", response_model=AgentResponse)
def ask(body: AgentRequest, user: User = Depends(get_current_user)):
    try:
        result = agent_ask(
            body.question,
            farmer_lat=body.latitude,
            farmer_lng=body.longitude,
        )
        return result
    except MetaAIUnavailable as exc:
        raise HTTPException(503, f"Agent unavailable: {exc}")
