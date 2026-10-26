"""
DigiLocker e-KYC — OAuth2 authorization-code flow. We only ever store the
DigiLocker transaction reference on the User row (User.kyc_reference_id),
never the underlying Aadhaar/ID document, matching the blueprint's "verify
without storing sensitive physical IDs" requirement.
"""
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()


class KycConfigError(RuntimeError):
    pass


class DigiLockerClient:
    def __init__(self):
        self.client_id = settings.DIGILOCKER_CLIENT_ID
        self.client_secret = settings.DIGILOCKER_CLIENT_SECRET
        self.base = settings.DIGILOCKER_API_BASE
        self.redirect_uri = settings.DIGILOCKER_REDIRECT_URI

    def _require_credentials(self):
        if not self.client_id or not self.client_secret:
            raise KycConfigError(
                "DIGILOCKER_CLIENT_ID / DIGILOCKER_CLIENT_SECRET not set. "
                "Register the app at https://partners.digilocker.gov.in"
            )

    def build_authorization_url(self, state: str) -> str:
        self._require_credentials()
        return (
            f"{self.base}/public/oauth2/1/authorize"
            f"?response_type=code&client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}&state={state}"
        )

    async def exchange_code_for_token(self, code: str) -> dict:
        self._require_credentials()
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{self.base}/public/oauth2/1/token", data=payload)
            resp.raise_for_status()
            return resp.json()  # contains access_token + a per-user DigiLocker txn/subject ref

    async def fetch_verified_identity(self, access_token: str) -> dict:
        """Returns only verification status + a reference id — the eaadhaar
        XML itself is never persisted by this backend."""
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.base}/public/oauth2/1/user", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return {"verified": True, "reference_id": data.get("digilockerid")}


digilocker_client = DigiLockerClient()
