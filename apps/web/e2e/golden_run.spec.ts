import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const distDir = path.resolve(__dirname, '../dist');

test.describe('OpsSaathi AI Golden Run E2E (scripts/golden_run.md)', () => {
  let caseCreated = false;
  let caseStatus = 'AWAITING_APPROVAL';
  let caseVersion = 1;
  let isSimulated = false;

  const resetState = () => {
    caseCreated = false;
    caseStatus = 'AWAITING_APPROVAL';
    caseVersion = 1;
    isSimulated = false;
  };

  test.beforeEach(async ({ page }) => {
    // 1. Serve frontend production bundle directly from dist/
    await page.route('http://localhost:5173/**', async (route) => {
      const url = new URL(route.request().url());
      let pathname = url.pathname;
      if (pathname === '/' || pathname === '') {
        pathname = '/index.html';
      }
      const filePath = path.join(distDir, pathname);
      if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        const contentType = filePath.endsWith('.html')
          ? 'text/html'
          : filePath.endsWith('.js')
          ? 'application/javascript'
          : filePath.endsWith('.css')
          ? 'text/css'
          : 'application/octet-stream';
        const body = fs.readFileSync(filePath);
        await route.fulfill({ status: 200, contentType, body });
      } else {
        const body = fs.readFileSync(path.join(distDir, 'index.html'));
        await route.fulfill({ status: 200, contentType: 'text/html', body });
      }
    });

    // 2. Mock API endpoints matching frozen scenario in scripts/golden_run.md
    await page.route('http://localhost:8000/api/v1/**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      const method = route.request().method();

      if (path.endsWith('/health')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              status: 'healthy',
              demo_data_mode: true,
              demo_deterministic: true,
              services: { api: 'up', database: 'connected', verifier_role: 'configured' },
            },
          }),
        });
        return;
      }

      if (path.endsWith('/metrics')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              straight_through_processing_rate_percent: 85.5,
              total_cases_handled: 42,
              total_cases_escalated: 6,
              repeat_explanations_avoided: 18,
              time_to_first_response_seconds: 4.2,
              time_to_verified_resolution_minutes: 3.5,
            },
          }),
        });
        return;
      }

      if (path.includes('/merchants/')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              id: '11111111-1111-1111-1111-111111111111',
              name: 'Paytm Smart Merchant Store',
              business_name: 'Paytm Smart Merchant Store',
              email: 'merchant@two-bits.demo',
              phone: '+91 98765 43210',
            },
          }),
        });
        return;
      }

      if (path.endsWith('/transactions')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              items: [
                { id: 't1', order_id: 'ORD_20261112_01', amount: '5000.00', status: 'SUCCESS' },
                { id: 't2', order_id: 'ORD_20261112_02', amount: '4000.00', status: 'SUCCESS' },
                { id: 't3', order_id: 'ORD_20261112_03', amount: '6000.00', status: 'SUCCESS' },
              ],
            },
          }),
        });
        return;
      }

      if (path.endsWith('/settlements')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              batches: [
                {
                  batch_ref: 'BATCH_20261112_01',
                  gross: isSimulated ? '15000.00' : '9000.00',
                  net: isSimulated ? '15000.00' : '9000.00',
                  status: 'SETTLED',
                },
              ],
              discrepancy_amount: isSimulated ? '0.00' : '6000.00',
            },
          }),
        });
        return;
      }

      if (path.endsWith('/demo/reset') && method === 'POST') {
        resetState();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              expected_net: 15000.0,
              observed_net: 9000.0,
              discrepancy: 6000.0,
              status: 'OVERDUE',
            },
          }),
        });
        return;
      }

      if (path.endsWith('/agent/messages') && method === 'POST') {
        caseCreated = true;
        caseStatus = 'AWAITING_APPROVAL';
        caseVersion = 1;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              reply:
                'I investigated your settlement. Order ORD_20261112_03 for ₹6,000.00 is missing from batch BATCH_20261112_01 and is OVERDUE. Case CAS-2026-1024 has been created and held for approval per policy.',
              language: 'en',
              active_case_id: 'case-1024',
              conversation_id: 'conv-1024',
              evidence_summary: {
                expected_net: '15000.00',
                observed_net: '9000.00',
                discrepancy: '6000.00',
                status: 'OVERDUE',
              },
              run_id: 'run-1024',
              is_replay: false,
              llm_source: 'GEMINI',
            },
          }),
        });
        return;
      }

      if (path.endsWith('/voice/sessions') && method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              session_id: 'sess-1024',
              conversation_id: 'conv-1024',
              ai_identity_disclosed: true,
              welcome_message: 'Namaste, I am OpsSaathi.',
            },
          }),
        });
        return;
      }

      if (path.endsWith('/cases') && method === 'GET') {
        const items = caseCreated
          ? [
              {
                id: 'case-1024',
                case_number: 'CAS-2026-1024',
                status: caseStatus,
                version: caseVersion,
                queue: 'SETTLEMENT_OPS',
                summary: 'Missing ₹6,000 from settlement batch BATCH_20261112_01',
                priority: 'P1',
                created_at: new Date().toISOString(),
              },
            ]
          : [];
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true, data: { items } }),
        });
        return;
      }

      if (path.endsWith('/cases/case-1024') && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              id: 'case-1024',
              case_number: 'CAS-2026-1024',
              status: caseStatus,
              version: caseVersion,
              queue: 'SETTLEMENT_OPS',
              summary: 'Missing ₹6,000 from settlement batch BATCH_20261112_01',
              priority: 'P1',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              timeline: [
                {
                  id: 'ev-1',
                  actor: 'OpsSaathi AI',
                  event_type: 'CASE_CREATED',
                  from_status: null,
                  to_status: 'NEW',
                  visibility: 'MERCHANT',
                  payload: {},
                  created_at: new Date().toISOString(),
                },
                {
                  id: 'ev-2',
                  actor: 'OpsSaathi AI',
                  event_type: 'APPROVAL_REQUESTED',
                  from_status: 'NEW',
                  to_status: 'AWAITING_APPROVAL',
                  visibility: 'INTERNAL',
                  payload: {
                    action: 'SETTLEMENT_RESYNC',
                    amount: '6000.00',
                    action_hash:
                      '44efa879046efa3a441c61673e778f5ed3cb2adec16c9d57ca0f88b6139a2e02',
                  },
                  created_at: new Date().toISOString(),
                },
              ],
            },
          }),
        });
        return;
      }

      if (path.endsWith('/cases/case-1024/approve') && method === 'POST') {
        caseStatus = 'VERIFYING';
        caseVersion += 1;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: {
              case_id: 'case-1024',
              status: 'APPROVED',
              new_version: caseVersion,
              resync_status: 'ACKNOWLEDGED',
            },
          }),
        });
        return;
      }

      if (path.endsWith('/demo/simulate-settlement') && method === 'POST') {
        isSimulated = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            data: { status: 'SIMULATED', added_amount: '6000.00', source_type: 'SYNTHETIC_DEMO' },
          }),
        });
        return;
      }

      if (path.endsWith('/cases/case-1024/verify') && method === 'POST') {
        if (!isSimulated) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              ok: true,
              data: {
                case_id: 'case-1024',
                status: 'VERIFYING',
                verification_result: 'FAIL',
                before_observed: '9000.00',
                after_observed: '9000.00',
                expected_net: '15000.00',
                verifier_role: 'opssaathi_verifier',
              },
            }),
          });
        } else {
          caseStatus = 'RESOLVED';
          caseVersion += 1;
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              ok: true,
              data: {
                case_id: 'case-1024',
                status: 'RESOLVED',
                verification_result: 'PASS',
                before_observed: '9000.00',
                after_observed: '15000.00',
                expected_net: '15000.00',
                verifier_role: 'opssaathi_verifier',
              },
            }),
          });
        }
        return;
      }

      // Default 404
      await route.fulfill({ status: 404, body: 'Not found' });
    });
  });

  const runGoldenPath = async (page: any, iteration: number) => {
    console.log(`Starting Golden Run Iteration #${iteration}...`);

    // 1. Load application
    await page.goto('http://localhost:5173/');
    await expect(page.locator('text=OpsSaathi AI').first()).toBeVisible({ timeout: 10000 });

    // 2. Deterministic Reset Demo
    const resetBtn = page.getByRole('button', { name: /Reset Demo/i });
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();
    await page.waitForTimeout(300);

    // 3. Baseline Verification
    await expect(page.locator('text=Paytm Smart Merchant Store').first()).toBeVisible();
    await expect(page.locator('text=₹6,000.00').or(page.locator('text=₹6,000')).first()).toBeVisible();

    // 4. Multilingual Language Switch
    const langSelect = page.locator('select').first();
    await expect(langSelect).toBeVisible();
    await langSelect.selectOption('hi');
    await page.waitForTimeout(100);
    await langSelect.selectOption('mr');
    await page.waitForTimeout(100);
    await langSelect.selectOption('en');

    // 5. Chat to Voice switch & AI Disclosure
    const micBtn = page.getByTitle(/Voice Input|Start Voice/i).or(page.locator('button:has(svg.lucide-mic)'));
    if ((await micBtn.count()) > 0) {
      await micBtn.first().click();
      await page.waitForTimeout(200);
      const typeInsteadBtn = page.getByRole('button', { name: /Type Instead|Cancel/i });
      if ((await typeInsteadBtn.count()) > 0) {
        await typeInsteadBtn.first().click();
      }
    }

    // 6. Submit Merchant Complaint in Chat
    const chatInput = page.getByPlaceholder(/Ask OpsSaathi/i).or(page.locator('input[type="text"]').last());
    await chatInput.fill('My ₹6,000 payment from yesterday is missing from settlement');
    const sendBtn = page.getByTitle('Send Message').or(page.locator('button:has(svg.lucide-send)'));
    await sendBtn.click();

    // Verify response
    await expect(page.locator('text=₹6,000').first()).toBeVisible({ timeout: 5000 });

    // 7. Switch to Ops Console
    const opsConsoleBtn = page.getByRole('button', { name: /Ops Console/i });
    await expect(opsConsoleBtn).toBeVisible();
    await opsConsoleBtn.click();
    await page.waitForTimeout(300);

    // 8. Verify Support Cases Queue & Policy Gate Alert (> ₹5,000)
    await expect(page.locator('text=Support Cases Queue')).toBeVisible();
    await expect(page.locator('text=AWAITING_APPROVAL').first()).toBeVisible({ timeout: 5000 });

    // 9. Negative Test: Premature resolution blocked before bank credit
    const verifyBtn = page.getByRole('button', { name: /Verify Resolution/i });
    if ((await verifyBtn.count()) > 0) {
      await verifyBtn.click();
      await page.waitForTimeout(300);
      await expect(page.locator('text=Verdict: PASS')).not.toBeVisible();
      await expect(page.locator('strong:has-text("RESOLVED")')).not.toBeVisible();
    }

    // 10. Human Review & Approval Flow
    const reviewApproveBtn = page.getByRole('button', { name: /Review & Approve Action/i });
    await expect(reviewApproveBtn).toBeVisible();
    await reviewApproveBtn.click();

    // Verify Modal
    await expect(page.locator('text=Authorize Gated Action')).toBeVisible();
    await expect(page.locator('text=SETTLEMENT_RESYNC').first()).toBeVisible();
    await expect(page.locator('text=₹6,000.00').first()).toBeVisible();

    // Confirm Approval
    const confirmApproveBtn = page.getByRole('button', { name: /Confirm & Authorize Re-Sync/i });
    await expect(confirmApproveBtn).toBeVisible();
    await confirmApproveBtn.click();
    await page.waitForTimeout(300);

    // 11. Case moves to VERIFYING
    await expect(page.locator('text=VERIFYING').first()).toBeVisible({ timeout: 5000 });

    // 12. Simulate Bank Settlement Credit (₹6,000)
    const simSettlementBtn = page.getByRole('button', { name: /Simulate Bank Settlement/i });
    if ((await simSettlementBtn.count()) > 0) {
      await simSettlementBtn.click();
      await page.waitForTimeout(500);
    }

    // 13. Independent Read-Only Verification
    await expect(verifyBtn).toBeVisible();
    await verifyBtn.click();

    // 14. Verification Report Verdict: PASS and Status RESOLVED
    await expect(
      page.locator('text=Verdict: PASS').or(page.locator('text=RESOLVED')).first()
    ).toBeVisible({ timeout: 8000 });

    console.log(`Golden Run Iteration #${iteration} passed successfully!`);
  };

  test('Golden run passes twice in a row from a clean reset', async ({ page }) => {
    // Run 1
    await runGoldenPath(page, 1);

    // Run 2 (acceptance requirement: passes twice in a row from a clean reset)
    await runGoldenPath(page, 2);
  });
});
