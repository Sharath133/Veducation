"""
Loyalty earn (referral), redeem, balance, and free-entry checkout behavior.
"""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models.duel import DailyDuel, Registration
from app.models.referral import LoyaltyTransaction, Referral
from app.models.user import User
from app.services.loyalty_service import LoyaltyService
from app.services.referral_service import ReferralService
from app.utils.security import create_access_token


def _auth_headers(user_id: uuid.UUID) -> dict:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def _make_user(
    db_session,
    *,
    mobile_suffix: str,
    referral_code: str,
    loyalty_points: int = 0,
    free_credits: int = 0,
) -> User:
    u = User(
        mobile_number=f"9{mobile_suffix}",
        referral_code=referral_code,
        loyalty_points=loyalty_points,
        free_duel_entry_credits=free_credits,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def test_referral_grants_points_and_ledger(db_session):
    referrer = _make_user(db_session, mobile_suffix="0000000001", referral_code="REF11111")
    referred = _make_user(db_session, mobile_suffix="0000000002", referral_code="REF22222")

    result = ReferralService.apply_referral_code(db_session, referred, "REF11111")

    assert result["success"] is True
    assert result["loyalty_points_added"] == 10
    db_session.refresh(referrer)
    db_session.refresh(referred)
    assert referred.referred_by_id == referrer.id
    assert referrer.loyalty_points == 10

    rows = (
        db_session.query(LoyaltyTransaction)
        .filter(LoyaltyTransaction.user_id == referrer.id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].transaction_type == "earned"
    assert int(rows[0].points) == 10
    assert rows[0].reference_id is not None

    ref_row = db_session.query(Referral).filter(Referral.referred_id == referred.id).one()
    assert ref_row.referrer_id == referrer.id


def test_redeem_insufficient_points_raises(db_session):
    user = _make_user(db_session, mobile_suffix="0000000003", referral_code="REF33333", loyalty_points=40)
    with pytest.raises(ValueError, match="Insufficient loyalty points"):
        LoyaltyService.redeem_for_free_duel_entry(db_session, user)


def test_redeem_success_updates_balance_and_ledger(db_session):
    user = _make_user(db_session, mobile_suffix="0000000004", referral_code="REF44444", loyalty_points=50)
    out = LoyaltyService.redeem_for_free_duel_entry(db_session, user)
    assert out["loyalty_points"] == 0
    assert out["free_duel_entry_credits"] == 1
    assert out["points_redeemed"] == 50

    db_session.refresh(user)
    assert user.loyalty_points == 0
    assert user.free_duel_entry_credits == 1

    ledger = (
        db_session.query(LoyaltyTransaction)
        .filter(LoyaltyTransaction.user_id == user.id, LoyaltyTransaction.transaction_type == "redeemed")
        .one()
    )
    assert int(ledger.points) == -50


def test_balance_payload_reflects_user(db_session):
    user = _make_user(
        db_session,
        mobile_suffix="0000000005",
        referral_code="REF55555",
        loyalty_points=25,
        free_credits=2,
    )
    payload = LoyaltyService.build_balance_payload(user)
    assert payload["loyalty_points"] == 25
    assert payload["free_duel_entry_credits"] == 2
    assert payload["points_per_free_entry"] == 50


def test_loyalty_api_balance_and_redeem(client: TestClient, db_session):
    user = _make_user(
        db_session,
        mobile_suffix="0000000006",
        referral_code="REF66666",
        loyalty_points=120,
        free_credits=0,
    )
    headers = _auth_headers(user.id)

    r = client.get("/api/v1/loyalty/points", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["loyalty_points"] == 120
    assert body["free_duel_entry_credits"] == 0

    r2 = client.post("/api/v1/loyalty/redeem", headers=headers)
    assert r2.status_code == 200
    redeemed = r2.json()
    assert redeemed["loyalty_points"] == 70
    assert redeemed["free_duel_entry_credits"] == 1

    r3 = client.get("/api/v1/loyalty/transactions", headers=headers)
    assert r3.status_code == 200
    types = {t["transaction_type"] for t in r3.json()["transactions"]}
    assert "redeemed" in types


def test_loyalty_redeem_api_insufficient_points(client: TestClient, db_session):
    user = _make_user(
        db_session,
        mobile_suffix="0000000007",
        referral_code="REF77777",
        loyalty_points=5,
    )
    r = client.post("/api/v1/loyalty/redeem", headers=_auth_headers(user.id))
    assert r.status_code == 400
    assert "Insufficient loyalty points" in r.json()["detail"]
    assert "5 points" in r.json()["detail"]


def test_free_entry_checkout_consumes_credit(client: TestClient, db_session):
    user = _make_user(
        db_session,
        mobile_suffix="0000000008",
        referral_code="REF88888",
        loyalty_points=0,
        free_credits=1,
    )
    duel = DailyDuel(duel_date="2099-01-01", registration_fee=Decimal("5.00"))
    db_session.add(duel)
    db_session.commit()
    db_session.refresh(duel)

    headers = _auth_headers(user.id)
    payload = {
        "duel_id": str(duel.id),
        "amount": "0",
        "name": "Test Player",
        "upi_mobile": "9123456789",
        "use_free_entry": True,
    }
    r = client.post("/api/v1/payment/create-order", json=payload, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("used_free_entry") is True
    assert data.get("order_id") is None

    db_session.refresh(user)
    assert user.free_duel_entry_credits == 0

    reg = (
        db_session.query(Registration)
        .filter(Registration.user_id == user.id, Registration.duel_id == duel.id)
        .one()
    )
    assert reg.payment_status == "completed"
    assert reg.payment_amount == Decimal("0.00")
