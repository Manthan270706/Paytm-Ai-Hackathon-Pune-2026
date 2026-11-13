# OpsSaathi AI: Autonomous Merchant Operations Teammate

**Team:** Two Bits  
**Event:** Paytm Build for India AI Hackathon – Pune Finale  
**Track:** Track 3: Autonomous AI Teammates  
**Date:** 15 November 2026  
**Venue:** Partex.AI, Midas Tower, Hinjawadi, Pune  

*Don't just respond. Investigate. Act. Coordinate. Verify.*

---

## 1. Overview

**OpsSaathi AI** is an autonomous operations teammate designed for the Paytm merchant ecosystem. Rather than acting as a standard FAQ chatbot, OpsSaathi investigates missing payments, performs deterministic `Decimal` reconciliation, enforces policy approvals via LangGraph checkpoints, executes cross-system settlement re-sync requests, and independently verifies the final resolution through a dedicated read-only database role.

### Key Capabilities
- **Multi-Modal Intake:** English, Hindi, and Marathi voice & chat intake with shared session memory.
- **Deterministic Reconciliation:** Core financial math uses `Decimal` (never hallucinated by an LLM).
- **Human-in-the-Loop Policy Gate:** High-value or risky actions require explicit approval from a Support Lead.
- **Independent Verification:** A ticket cannot reach `RESOLVED` without a fresh backend verification `PASS` by the `opssaathi_verifier` read-only role.
- **Auditable Provenance:** Every financial record is explicitly tagged as `PAYTM_STAGING` or `SYNTHETIC_DEMO`.

---

## 2. Architecture

```
  [ Merchant: Chat / Voice ]                [ Paytm Support Operations ]
              │                                          │
              ▼                                          ▼
   React + Vite + TypeScript               Support & Ops Console
   (Mobile Merchant UI)                    (Approvals & Audit Events)
              │                                          │
              └────────────────────┬─────────────────────┘
                                   │ HTTPS REST + SSE Live Trace
                                   ▼
                       FastAPI Backend Service
               (Auth, RBAC, ScopedRepository, Redaction)
                                   │
                                   ▼
                     LangGraph Supervisor Workflow
        (Intake -> Investigate -> Reconcile -> Policy -> Action -> Verify)
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
          PostgreSQL Database           Integration Adapters
     • Scoped Merchant Records       • Paytm Staging API / Webhooks
     • Synthetic Settlement Ledger   • Gemini API (LLM)
     • Cases, Versioning, Audits     • Sarvam AI (Indian Voice STT/TTS)
     • Read-Only Verifier Role       • Mock Settlement Ops Adapter
```

---

## 3. Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional for local zero-Docker run)

### Running with Docker Compose
```bash
# 1. Clone & copy environment configuration
cp .env.example .env

# 2. Start PostgreSQL, API, and Frontend
docker compose -f infra/docker-compose.yml up --build

# 3. Access applications
# Web UI:     http://localhost:5173
# FastAPI:    http://localhost:8000/docs
# Health API: http://localhost:8000/api/v1/health
```

### Running Locally (Without Docker)
```bash
# Backend (FastAPI)
cd services/api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (React + Vite)
cd apps/web
npm install
npm run dev
```

---

## 4. Frozen Seed Scenario (Golden Path)
- **Merchant:** Ramesh Kirana Store
- **Eligible Captures:** ₹15,000.00
- **Observed in Ledger:** ₹9,000.00
- **Discrepancy:** ₹6,000.00 (`OVERDUE`)
- **Policy Threshold:** ₹5,000.00 (triggers human approval checkpoint)
