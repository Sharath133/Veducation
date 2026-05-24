"""
RazorpayX payout API client (Basic auth; secrets from environment only).
"""
from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from typing import Any, Mapping, MutableMapping

logger = logging.getLogger(__name__)


class RazorpayPayoutError(RuntimeError):
    """Raised when Razorpay returns a non-success response."""

    def __init__(self, message: str, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class RazorpayPayoutClient:
    """
    Minimal client for POST /v1/payouts (RazorpayX).
    Requires live mode keys and a configured fund account per user.
    """

    _BASE = "https://api.razorpay.com/v1"

    def __init__(self, key_id: str, key_secret: str, razorpayx_account_id: str = ""):
        self._key_id = (key_id or "").strip()
        self._key_secret = (key_secret or "").strip()
        self._account_id = (razorpayx_account_id or "").strip()

    def create_payout(
        self,
        *,
        fund_account_id: str,
        amount_paise: int,
        reference_id: str,
        narration: str,
        currency: str = "INR",
        mode: str = "IMPS",
    ) -> Mapping[str, Any]:
        if not self._key_id or not self._key_secret:
            raise RazorpayPayoutError("Razorpay API credentials are not configured")
        if amount_paise <= 0:
            raise RazorpayPayoutError("Payout amount must be positive")
        payload: dict[str, Any] = {
            "fund_account_id": fund_account_id,
            "amount": int(amount_paise),
            "currency": currency,
            "mode": mode,
            "purpose": "payout",
            "reference_id": reference_id[:40],
            "narration": narration[:30],
            "queue_if_low_balance": True,
        }
        return self._post_json("payouts", payload)

    def _post_json(self, path: str, payload: MutableMapping[str, Any]) -> Mapping[str, Any]:
        url = f"{self._BASE}/{path.lstrip('/')}"
        raw = json.dumps(payload).encode("utf-8")
        token = base64.b64encode(f"{self._key_id}:{self._key_secret}".encode("utf-8")).decode("ascii")
        headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
        if self._account_id:
            headers["X-Razorpay-Account"] = self._account_id
        req = urllib.request.Request(url, data=raw, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.warning("Razorpay payout HTTP error %s: %s", e.code, err_body)
            raise RazorpayPayoutError("Razorpay payout request failed", status_code=e.code, body=err_body) from e
        except urllib.error.URLError as e:
            logger.error("Razorpay payout network error: %s", e)
            raise RazorpayPayoutError("Razorpay payout network error") from e
