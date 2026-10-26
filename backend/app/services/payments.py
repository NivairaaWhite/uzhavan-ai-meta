"""
Razorpay client for UPI collection + escrow-style holds + payout to
farmers. Razorpay's actual escrow primitive is "Route" (split settlements
held until a release trigger) — this wraps that, not a generic guess.

Every method requires RAZORPAY_KEY_ID/SECRET (from the Razorpay
dashboard, sandbox first). No method fabricates a response if
credentials are missing — it raises, so a misconfigured deployment fails
loudly instead of pretending payments succeeded.
"""
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()


class PaymentConfigError(RuntimeError):
    pass


class RazorpayClient:
    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.base = settings.RAZORPAY_API_BASE

    def _auth(self):
        if not self.key_id or not self.key_secret:
            raise PaymentConfigError(
                "RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not set. "
                "Create sandbox keys at https://dashboard.razorpay.com/app/keys"
            )
        return (self.key_id, self.key_secret)

    async def create_order(self, amount_rupees: float, receipt: str, notes: Optional[dict] = None) -> dict:
        """Amount is rupees in our domain; Razorpay wants paise (int)."""
        auth = self._auth()
        payload = {
            "amount": int(round(amount_rupees * 100)),
            "currency": "INR",
            "receipt": receipt,
            "notes": notes or {},
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{self.base}/orders", json=payload, auth=auth)
            resp.raise_for_status()
            return resp.json()

    async def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        import hmac
        import hashlib
        auth = self._auth()  # ensures secret is present before we use it below
        body = f"{order_id}|{payment_id}"
        expected = hmac.new(self.key_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def create_route_transfer(self, payment_id: str, farmer_account_id: str, amount_rupees: float) -> dict:
        """Escrow release: split the held payment to the farmer's linked
        Razorpay Route account once delivery is confirmed."""
        auth = self._auth()
        payload = {"transfers": [{
            "account": farmer_account_id,
            "amount": int(round(amount_rupees * 100)),
            "currency": "INR",
            "on_hold": False,
        }]}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{self.base}/payments/{payment_id}/transfers", json=payload, auth=auth)
            resp.raise_for_status()
            return resp.json()

    async def disburse_imps(self, fund_account_id: str, amount_rupees: float, reference_id: str) -> dict:
        """Direct IMPS payout via RazorpayX, for cases with no linked
        Route sub-account (e.g. one-off buyer refunds)."""
        auth = self._auth()
        payload = {
            "account_number": settings.RAZORPAY_KEY_ID,  # source virtual account, prod: real XA/XB acct
            "fund_account_id": fund_account_id,
            "amount": int(round(amount_rupees * 100)),
            "currency": "INR",
            "mode": "IMPS",
            "purpose": "payout",
            "reference_id": reference_id,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post("https://api.razorpay.com/v1/payouts", json=payload, auth=auth)
            resp.raise_for_status()
            return resp.json()


razorpay_client = RazorpayClient()
