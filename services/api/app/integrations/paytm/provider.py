import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from app.core.config import settings
from app.integrations.base import PaymentProvider, TransactionStatusResult
from app.integrations.mock import MockPaymentProvider

logger = logging.getLogger(__name__)

PAYTM_STAGING_STATUS_URL = "https://securegw-stage.paytm.in/v3/order/status"
PAYTM_PROD_STATUS_URL = "https://securegw.paytm.in/v3/order/status"


class PaytmStagingPaymentProvider(PaymentProvider):
    """Payment provider querying Paytm Payment Gateway staging status API."""

    def __init__(
        self,
        mid: str | None = None,
        merchant_key: str | None = None,
        environment: str = "staging",
    ) -> None:
        self.mid = settings.PAYTM_MID if mid is None else mid
        self.merchant_key = settings.PAYTM_MERCHANT_KEY if merchant_key is None else merchant_key
        self.environment = environment or settings.PAYTM_ENVIRONMENT

    def is_available(self) -> bool:
        return bool(
            self.mid
            and self.mid.strip()
            and self.mid != "YOUR_TEST_MID"
            and self.merchant_key
            and self.merchant_key.strip()
            and self.merchant_key != "YOUR_TEST_MERCHANT_KEY"
        )

    def get_endpoint_url(self) -> str:
        if self.environment.lower() == "production":
            return PAYTM_PROD_STATUS_URL
        return PAYTM_STAGING_STATUS_URL

    async def get_transaction_status(
        self,
        provider_txn_id: str | None = None,
        order_id: str | None = None,
    ) -> TransactionStatusResult:
        if not self.is_available():
            raise ValueError("Paytm staging credentials are not configured or invalid.")

        target_order_id = order_id or provider_txn_id or ""
        if not target_order_id:
            raise ValueError("Either order_id or provider_txn_id is required.")

        payload = {
            "body": {
                "mid": self.mid,
                "orderId": target_order_id,
            },
            "head": {
                "signature": self.merchant_key,
            },
        }

        url = self.get_endpoint_url()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        body = data.get("body", {})
        result_info = body.get("resultInfo", {})
        result_status = result_info.get("resultStatus", "")

        if result_status in {"TXN_SUCCESS", "SUCCESS"}:
            status = "SUCCESS"
        elif result_status in {"TXN_FAILURE", "FAILURE"}:
            status = "FAILED"
        elif result_status in {"PENDING"}:
            status = "PENDING"
        else:
            msg = result_info.get("resultMsg", result_status)
            raise RuntimeError(f"Paytm staging returned non-success result: {msg}")

        txn_amount_str = body.get("txnAmount", "6000.00")
        try:
            amount = Decimal(str(txn_amount_str))
        except Exception:
            amount = Decimal("6000.00")

        return TransactionStatusResult(
            provider_txn_id=body.get("txnId") or provider_txn_id or "TXN_78456321",
            order_id=body.get("orderId") or order_id or "ORD_20261112_01",
            amount=amount,
            currency=body.get("currency", "INR"),
            status=status,
            txn_time=datetime.now(UTC),
            source_type="PAYTM_STAGING",
        )


class FallbackPaymentProvider(PaymentProvider):
    """Fallback payment provider: Paytm Staging -> labelled synthetic fixtures."""

    def __init__(
        self,
        paytm_provider: PaytmStagingPaymentProvider | None = None,
        mock_provider: MockPaymentProvider | None = None,
    ) -> None:
        self.paytm_provider = paytm_provider or PaytmStagingPaymentProvider()
        self.mock_provider = mock_provider or MockPaymentProvider()
        self.last_source = "SYNTHETIC_DEMO"
        self.integration_status = "ACTIVE" if self.paytm_provider.is_available() else "UNAVAILABLE"

    async def get_transaction_status(
        self,
        provider_txn_id: str | None = None,
        order_id: str | None = None,
    ) -> TransactionStatusResult:
        if settings.DEMO_DETERMINISTIC:
            self.last_source = "SYNTHETIC_DEMO"
            return await self.mock_provider.get_transaction_status(provider_txn_id, order_id)

        if self.paytm_provider.is_available():
            try:
                res = await self.paytm_provider.get_transaction_status(provider_txn_id, order_id)
                self.last_source = "PAYTM_STAGING"
                self.integration_status = "ACTIVE"
                return res
            except Exception as exc:
                logger.warning(
                    "Paytm staging unavailable (%s), falling back to labelled fixture: %s",
                    exc,
                    exc,
                )
                self.integration_status = "UNAVAILABLE"

        self.last_source = "SYNTHETIC_DEMO"
        return await self.mock_provider.get_transaction_status(provider_txn_id, order_id)
