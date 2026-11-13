from decimal import Decimal
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.integrations.mock import MockPaymentProvider
from app.integrations.paytm.provider import (
    FallbackPaymentProvider,
    PaytmStagingPaymentProvider,
)
from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-token-merchant-1"}


async def test_paytm_staging_adapter_credentials_check() -> None:
    """Verify that credentials are checked and unconfigured provider raises ValueError."""
    prov_empty = PaytmStagingPaymentProvider(mid="", merchant_key="")
    assert not prov_empty.is_available()

    with pytest.raises(ValueError, match="Paytm staging credentials are not configured"):
        await prov_empty.get_transaction_status(order_id="ORD_123")

    prov_dummy = PaytmStagingPaymentProvider(
        mid="YOUR_TEST_MID", merchant_key="YOUR_TEST_MERCHANT_KEY"
    )
    assert not prov_dummy.is_available()


async def test_paytm_staging_successful_mocked_lookup() -> None:
    """Verify that successful staging lookup returns TransactionStatusResult with PAYTM_STAGING."""
    paytm_prov = PaytmStagingPaymentProvider(
        mid="DIY12386817555501617",
        merchant_key="valid-staging-key",
        environment="staging",
    )
    assert paytm_prov.is_available()

    mock_resp_json = {
        "body": {
            "resultInfo": {
                "resultStatus": "TXN_SUCCESS",
                "resultCode": "01",
                "resultMsg": "Txn Successful",
            },
            "txnId": "TXN_STAGING_999888",
            "orderId": "ORD_STAGING_001",
            "txnAmount": "6000.00",
            "currency": "INR",
        }
    }

    async def mock_post(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("POST", url)
        return httpx.Response(200, json=mock_resp_json, request=req)

    with patch.object(httpx.AsyncClient, "post", side_effect=mock_post):
        result = await paytm_prov.get_transaction_status(order_id="ORD_STAGING_001")
        assert result.provider_txn_id == "TXN_STAGING_999888"
        assert result.order_id == "ORD_STAGING_001"
        assert result.amount == Decimal("6000.00")
        assert result.status == "SUCCESS"
        # Acceptance: source badge reflects real origin
        assert result.source_type == "PAYTM_STAGING"


async def test_paytm_staging_unavailable_falls_back_to_labelled_fixture() -> None:
    """Verify that when staging fails or is unavailable, labelled SYNTHETIC_DEMO fixture is used."""
    paytm_prov = PaytmStagingPaymentProvider(
        mid="DIY12386817555501617",
        merchant_key="valid-staging-key",
    )
    fallback_prov = FallbackPaymentProvider(
        paytm_provider=paytm_prov,
        mock_provider=MockPaymentProvider(),
    )

    async def mock_post_err(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("POST", url)
        return httpx.Response(503, text="Service Unavailable", request=req)

    with patch.object(httpx.AsyncClient, "post", side_effect=mock_post_err):
        result = await fallback_prov.get_transaction_status(order_id="ORD_20261112_01")
        # Acceptance: Never silently mix sources; explicitly labelled as SYNTHETIC_DEMO
        assert result.source_type == "SYNTHETIC_DEMO"
        assert result.amount == Decimal("6000.00")
        assert fallback_prov.last_source == "SYNTHETIC_DEMO"
        assert fallback_prov.integration_status == "UNAVAILABLE"


async def test_deterministic_mode_forces_synthetic_demo() -> None:
    """Verify DEMO_DETERMINISTIC bypasses live calls and serves labelled fixtures."""
    original_deterministic = settings.DEMO_DETERMINISTIC
    settings.DEMO_DETERMINISTIC = True
    try:
        fallback_prov = FallbackPaymentProvider()
        result = await fallback_prov.get_transaction_status(order_id="ORD_20261112_01")
        assert result.source_type == "SYNTHETIC_DEMO"
        assert result.amount == Decimal("6000.00")
        assert fallback_prov.last_source == "SYNTHETIC_DEMO"
    finally:
        settings.DEMO_DETERMINISTIC = original_deterministic


async def test_health_endpoint_reflects_payment_provider() -> None:
    """Verify /health reflects payment provider status and active origin."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "payment_provider" in data
        payment_info = data["payment_provider"]
        assert "active" in payment_info
        assert "status" in payment_info
        assert payment_info["environment"] == "staging"
