# OpsSaathi AI - Golden Run Specification (`scripts/golden_run.md`)

This runbook defines the exact step-by-step end-to-end execution path for judging and live evaluation at the Paytm Build for India AI Hackathon (Track 3: Autonomous AI Teammates).

---

## 1. Frozen Scenario Baseline Data

| Metric / Attribute | Value | Provenance / Rule |
| :--- | :--- | :--- |
| **Merchant Name** | Two Bits Chai & Snacks | Seeded profile (`MID_DEMO_TWOBITS`) |
| **Merchant UUID** | `11111111-1111-1111-1111-111111111111` | Deterministic UUID |
| **Eligible Payments** | ₹15,000.00 | 3 Txns: ₹5,000 (`TXN_78456319`), ₹4,000 (`TXN_78456320`), ₹6,000 (`TXN_78456321`) |
| **Observed in Ledger** | ₹9,000.00 | Batch `BATCH_20261112_01` has Txn 1 and Txn 2 only |
| **Discrepancy** | **₹6,000.00** | Missing payout for order `ORD_20261112_03` |
| **Reason Code** | `OVERDUE` | Expected settlement date (`2026-11-13`) has already passed |
| **Policy Threshold** | ₹5,000.00 | Discrepancy ₹6,000 > ₹5,000 $\rightarrow$ `REQUIRE_APPROVAL` |
| **Verification Gate** | Read-only check | Resolution cannot be marked `RESOLVED` until verifier sees ₹0 diff |

---

## 2. Step-by-Step Golden Run

### Step 1: Deterministic Reset & Seed
- **Action**: Call demo reset endpoint (support role) or execute CLI seed.
  - API: `POST /api/v1/demo/reset` with header `Authorization: Bearer demo-token-support_agent-1`
  - CLI: `python scripts/seed_demo.py --sqlite`
- **Expected Result**:
  - HTTP `200 OK`
  - Response body contains:
    ```json
    {
      "ok": true,
      "data": {
        "expected_net": 15000.0,
        "observed_net": 9000.0,
        "discrepancy": 6000.0,
        "status": "OVERDUE"
      },
      "meta": { "source_type": "SYNTHETIC_DEMO" }
    }
    ```

### Step 2: Merchant Authentication & Dashboard
- **Action**: Start merchant demo session.
  - API: `POST /api/v1/auth/demo-login` with payload `{"role": "merchant"}`
- **Expected Result**:
  - Bearer token issued for `merchant@two-bits.demo` bound to tenant `Two Bits Chai & Snacks`.
  - Dashboard shows: Expected ₹15,000, Settled ₹9,000, Discrepancy ₹6,000.

### Step 3: Merchant Complaint (Multilingual Chat or Voice)
- **Action**: Merchant sends voice or typed complaint.
  - English: *"My ₹6,000 payment is missing from yesterday's settlement."*
  - Hindi: *"मेरा ₹6,000 का सेटलमेंट क्यों रुका हुआ है?"*
  - Marathi: *"माझा ₹६,००० चा सेटलमेंट का अडकला आहे?"*
  - API: `POST /api/v1/agent/message` with `{"channel": "chat", "message": "My ₹6,000 payment is missing from yesterday's settlement."}`
- **Expected Result**:
  - Live SSE trace streams tool executions:
    1. `get_merchant_context()` $\rightarrow$ merchant scope bound server-side.
    2. `find_transactions()` $\rightarrow$ locates `ORD_20261112_03` (`TXN_78456321`, ₹6,000.00, `SUCCESS`).
    3. `get_settlement_entries()` $\rightarrow$ confirms batch `BATCH_20261112_01` contains only ₹9,000.
    4. `calculate_discrepancy()` $\rightarrow$ computes exact ₹6,000.00 discrepancy with `OVERDUE` status.
  - Agent replies explaining that ₹6,000 payout from order `ORD_20261112_03` was omitted from batch `BATCH_20261112_01`.

### Step 4: Policy Gate & Support Case Creation
- **Action**: Agent initiates autonomous remediation workflow.
- **Expected Result**:
  - `create_support_case()` executes: Case created with status `AWAITING_APPROVAL`, category `SETTLEMENT_DELAY`.
  - Policy engine evaluates re-sync request:
    - Action: `SETTLEMENT_RESYNC`
    - Amount: ₹6,000.00 > Threshold ₹5,000.00
    - Decision: `REQUIRE_APPROVAL`
  - Workflow safely pauses at approval checkpoint; action hash and case version recorded.

### Step 5: Support Console Review & Approval
- **Action**: Switch to Support Lead view.
  - API: `POST /api/v1/auth/demo-login` with `{"role": "support_agent"}`
  - GET `/api/v1/cases/pending-approval`
- **Expected Result**:
  - Support dashboard displays pending re-sync for ₹6,000.00 on `Two Bits Chai & Snacks`.
  - Human reviewer reviews evidence trace and clicks **Approve**.
  - `POST /api/v1/cases/{case_id}/approve`
  - Workflow resumes:
    - Version & action hash verified (anti-tamper).
    - Mock Settlement Ops adapter receives re-sync request $\rightarrow$ returns `ACKNOWLEDGED`.
    - Case transitions to `VERIFYING`.

### Step 6: Negative Test - Premature Close Prevented
- **Action**: Attempt to prematurely close or resolve case before verification PASS.
  - API: `POST /api/v1/cases/{case_id}/resolve`
- **Expected Result**:
  - Request rejected with HTTP `403 FORBIDDEN` or policy error: *"Case cannot be resolved without verification PASS."*

### Step 7: Simulate Bank Settlement
- **Action**: Simulate bank-side credit to batch (requires support role).
  - API: `POST /api/v1/demo/simulate-settlement` with header `Authorization: Bearer demo-token-support_agent-1`
- **Expected Result**:
  - Missing ₹6,000 entry inserted as `SYNTHETIC_DEMO`.
  - Batch net updated to ₹15,000.00.
  - Audit trail records `SIMULATE_BANK_SETTLEMENT`.

### Step 8: Independent Read-Only Verification
- **Action**: Run verification engine (requires authenticated session).
  - API: `POST /api/v1/cases/{case_id}/verify` with header `Authorization: Bearer demo-token-support_agent-1`
- **Expected Result**:
  - Query executes strictly through `opssaathi_verifier` role (SELECT-only).
  - Before: Discrepancy ₹6,000.00
  - After: Discrepancy ₹0.00
  - Status: **`PASS`**
  - Evidence timestamp recorded.

### Step 9: Case Resolved & Merchant Notified
- **Action**: Finalize case resolution.
- **Expected Result**:
  - Case status becomes `RESOLVED`.
  - Timeline displays full tamper-evident audit history.
  - Notification dispatched to merchant in their preferred language.

---

## 3. Test Verification Commands

```bash
# 1. Integrity guard check
python scripts/guard.py

# 2. Database seed verification
python scripts/seed_demo.py --sqlite

# 3. Full test suite execution
pytest services/api/app/tests -v
```
