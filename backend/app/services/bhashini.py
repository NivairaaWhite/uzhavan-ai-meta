"""
Bhashini client — real speech-to-text / translate / text-to-speech for
Indian languages via the government Bhashini/Dhruva pipeline.

Auth flow (as published by MeitY): you call the ULCA "pipeline config"
endpoint once with your user-id/api-key to get back a per-request
inference key + the actual model endpoint to call, then call that
endpoint for ASR/NMT/TTS. This client implements exactly that two-step
flow. It requires real BHASHINI_USER_ID / BHASHINI_API_KEY (issued at
bhashini.gov.in) to do anything — without them every method raises
BhashiniAuthError immediately rather than silently returning fake data.
"""
import base64
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()


class BhashiniAuthError(RuntimeError):
    pass


class BhashiniClient:
    def __init__(self):
        self.user_id = settings.BHASHINI_USER_ID
        self.api_key = settings.BHASHINI_API_KEY
        self.auth_base = settings.BHASHINI_API_BASE
        self.infer_base = settings.BHASHINI_INFERENCE_BASE

    def _require_credentials(self):
        if not self.user_id or not self.api_key:
            raise BhashiniAuthError(
                "BHASHINI_USER_ID / BHASHINI_API_KEY are not set. "
                "Register at https://bhashini.gov.in to obtain them."
            )

    async def _get_pipeline_config(self, task: str, source_lang: str, target_lang: Optional[str] = None):
        self._require_credentials()
        payload = {
            "pipelineTasks": [{
                "taskType": task,
                "config": {
                    "language": {"sourceLanguage": source_lang, **({"targetLanguage": target_lang} if target_lang else {})}
                },
            }],
            "pipelineRequestConfig": {"pipelineId": "64392f96daac500b55c543cd"},
        }
        headers = {"userID": self.user_id, "ulcaApiKey": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{self.auth_base}/ulca/apis/v0/model/getModelsPipeline", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def speech_to_text(self, audio_bytes: bytes, language: Optional[str] = None) -> str:
        """Streaming/websocket ASR is used by the mobile app directly for
        live dictation (see mobile/lib/services/voice_service.dart); this
        REST path is for short queued voice notes synced from offline
        storage."""
        language = language or settings.BHASHINI_DEFAULT_LANG
        config = await self._get_pipeline_config("asr", language)
        endpoint = config["pipelineInferenceAPIEndPoint"]["callbackUrl"]
        inference_key = config["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]
        audio_b64 = base64.b64encode(audio_bytes).decode()

        body = {
            "pipelineTasks": [{"taskType": "asr", "config": {"language": {"sourceLanguage": language}}}],
            "inputData": {"audio": [{"audioContent": audio_b64}]},
        }
        headers = {"Authorization": inference_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(endpoint, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["pipelineResponse"][0]["output"][0]["source"]

    async def text_to_speech(self, text: str, language: Optional[str] = None) -> bytes:
        language = language or settings.BHASHINI_DEFAULT_LANG
        config = await self._get_pipeline_config("tts", language)
        endpoint = config["pipelineInferenceAPIEndPoint"]["callbackUrl"]
        inference_key = config["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]

        body = {
            "pipelineTasks": [{"taskType": "tts", "config": {"language": {"sourceLanguage": language}}}],
            "inputData": {"input": [{"source": text}]},
        }
        headers = {"Authorization": inference_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(endpoint, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            audio_b64 = data["pipelineResponse"][0]["audio"][0]["audioContent"]
            return base64.b64decode(audio_b64)

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        config = await self._get_pipeline_config("translation", source_lang, target_lang)
        endpoint = config["pipelineInferenceAPIEndPoint"]["callbackUrl"]
        inference_key = config["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]

        body = {
            "pipelineTasks": [{
                "taskType": "translation",
                "config": {"language": {"sourceLanguage": source_lang, "targetLanguage": target_lang}},
            }],
            "inputData": {"input": [{"source": text}]},
        }
        headers = {"Authorization": inference_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(endpoint, json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()["pipelineResponse"][0]["output"][0]["target"]


bhashini_client = BhashiniClient()
