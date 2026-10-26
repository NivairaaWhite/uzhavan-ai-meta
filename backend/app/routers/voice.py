"""
Voice router: Tamil speech-to-text relay (Muse Voice Transcribe),
intent extraction (Spark 1.3), and text-to-speech (Bhashini).
"""
import asyncio
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import get_current_user, user_from_token
from app.config import get_settings
from app.database import SessionLocal
from app.models import User
from app.services.bhashini import bhashini_client, BhashiniAuthError
from app.services.meta_ai import ask_json, MetaAIUnavailable

router = APIRouter(prefix="/voice", tags=["voice"])
settings = get_settings()

ASR_URL = "wss://api.meta.ai/v1/asr/realtime"


class TranscriptIn(BaseModel):
    transcript: str


class SpeakIn(BaseModel):
    text: str
    lang: str = "ta"


class HarvestIntent(BaseModel):
    crop_type: Optional[
        Literal["tomato", "onion", "paddy", "brinjal", "banana", "chilli"]
    ] = None
    quantity_kg: Optional[float] = None
    district: Optional[str] = None
    missing: list[str] = []


INTENT_SYSTEM = (
    "Extract a harvest report from what a farmer says (Tamil, English or mixed). "
    "Crops: தக்காளி=tomato, வெங்காயம்=onion, நெல்=paddy, கத்தரிக்காய்=brinjal, வாழை=banana, மிளகாய்=chilli. "
    "1 quintal = 100 kg, 1 tonne = 1000 kg. A bag (மூட்டை) has no fixed weight, so leave quantity_kg null. "
    "List anything you could not determine in missing. Never guess."
)


@router.post("/intent", response_model=HarvestIntent)
def intent(body: TranscriptIn, user: User = Depends(get_current_user)):
    try:
        return ask_json(HarvestIntent, INTENT_SYSTEM, body.transcript)
    except MetaAIUnavailable:
        raise HTTPException(503, "Voice understanding is unavailable right now")


@router.post("/speak")
async def speak(body: SpeakIn, user: User = Depends(get_current_user)):
    try:
        audio = await bhashini_client.text_to_speech(body.text, body.lang)
    except BhashiniAuthError:
        raise HTTPException(503, "Text-to-speech is not configured")
    return Response(content=audio, media_type="audio/wav")


@router.websocket("/stream")
async def stream(ws: WebSocket, token: str, lang: str = "Tamil"):
    with SessionLocal() as db:
        user = user_from_token(token, db)
    if user is None or not settings.META_AI_ENABLED:
        await ws.close(code=4401)
        return
    await ws.accept()

    try:
        import websockets
    except ImportError:
        await ws.close(code=4500)
        return

    try:
        async with websockets.connect(
            ASR_URL,
            additional_headers={"Authorization": f"Bearer {settings.MODEL_API_KEY}"},
        ) as upstream:
            async def up():
                while True:
                    data = await ws.receive_bytes()
                    await upstream.send(data)

            async def down():
                async for msg in upstream:
                    text = msg if isinstance(msg, str) else msg.decode("utf-8", errors="replace")
                    await ws.send_json({"type": "final_transcript", "text": text})

            await asyncio.gather(up(), down())
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await ws.close(code=1011)
