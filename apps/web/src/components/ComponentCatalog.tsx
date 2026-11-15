import { FC, useState } from 'react'
import { Button } from './Button'
import { Input } from './Input'
import { Card } from './Card'
import { ListRow } from './ListRow'
import { StatusChip, CaseStatus } from './StatusChip'
import { SourceBadge } from './SourceBadge'
import { Modal } from './Modal'
import { Toast, ToastVariant } from './Toast'
import { Skeleton } from './Skeleton'
import { EmptyState } from './EmptyState'
import { ErrorState } from './ErrorState'
import { ArrowLeft } from 'lucide-react'

interface ComponentCatalogProps {
  onBack?: () => void
}

export const ComponentCatalog: FC<ComponentCatalogProps> = ({ onBack }) => {
  const [inputValue, setInputValue] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [toastState, setToastState] = useState<{
    isOpen: boolean
    variant: ToastVariant
    title: string
    message: string
  }>({
    isOpen: false,
    variant: 'info',
    title: '',
    message: '',
  })
  const [activeCardAction, setActiveCardAction] = useState<string | null>(null)

  const showToast = (variant: ToastVariant, title: string, message: string) => {
    setToastState({ isOpen: true, variant, title, message })
  }

  const allStatuses: CaseStatus[] = [
    'NEW',
    'IN_PROGRESS',
    'AWAITING_APPROVAL',
    'APPROVED',
    'VERIFYING',
    'RESOLVED',
    'REJECTED',
    'CANCELLED',
  ]

  return (
    <div className="w-full max-w-5xl mx-auto p-4 sm:p-6 lg:p-8 space-y-10 font-sans text-ink-primary">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-surface-divider">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-paytm-cyan" />
            <h1 className="text-2xl font-bold text-paytm-navy tracking-tight">
              OpsSaathi Component Gallery
            </h1>
          </div>
          <p className="text-sm text-ink-secondary mt-1">
            Paytm-aligned tokens: Navy <span className="font-mono text-xs">#002E6E</span>, Cyan <span className="font-mono text-xs">#00BAF2</span>. Zero arbitrary hex; WCAG AA compliant.
          </p>
        </div>

        {onBack && (
          <Button variant="secondary" onClick={onBack} className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            Back to App
          </Button>
        )}
      </div>

      {/* 1. Base Controls (Button, Input) */}
      <section className="space-y-4">
        <div className="border-b border-surface-divider pb-2">
          <h2 className="text-lg font-semibold text-paytm-navy">1. Base Controls (Buttons & Inputs)</h2>
          <p className="text-xs text-ink-secondary">Touch targets 48px min-height, focus ring in Cyan.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card title="Button Variants">
            <div className="flex flex-wrap gap-3 pt-2">
              <Button
                variant="primary"
                onClick={() => showToast('success', 'Primary Action', 'Primary button clicked')}
              >
                Primary Button
              </Button>
              <Button
                variant="secondary"
                onClick={() => showToast('info', 'Secondary Action', 'Secondary button clicked')}
              >
                Secondary Button
              </Button>
              <Button
                variant="ghost"
                onClick={() => showToast('warning', 'Ghost Action', 'Ghost button clicked')}
              >
                Ghost Button
              </Button>
              <Button variant="primary" disabled>
                Disabled
              </Button>
            </div>
          </Card>

          <Card title="Text Input Control">
            <div className="space-y-4 pt-2">
              <Input
                id="catalog-input"
                label="Settlement or UTR Reference"
                placeholder="e.g. BATCH_20261112_01"
                value={inputValue}
                onChange={setInputValue}
              />
              <p className="text-xs text-ink-muted">
                Current value: <span className="font-mono text-ink-primary">{inputValue || '(none)'}</span>
              </p>
            </div>
          </Card>
        </div>
      </section>

      {/* 2. Cards & List Rows */}
      <section className="space-y-4">
        <div className="border-b border-surface-divider pb-2">
          <h2 className="text-lg font-semibold text-paytm-navy">2. Cards & List Rows</h2>
          <p className="text-xs text-ink-secondary">Indian currency formatting with right-aligned amounts.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card
            title="Interactive Card (Click or Enter/Space)"
            onActivate={() => {
              setActiveCardAction('Activated card via click or keyboard')
              showToast('success', 'Card Activated', 'Card received activation event')
            }}
          >
            <div className="pt-2">
              <p className="text-xs text-ink-muted mb-2">
                Demonstrates keyboard tab stop and Enter/Space trigger
              </p>
              <p className="text-sm text-ink-secondary">
                Cards support optional <code className="text-xs bg-surface-subtle px-1.5 py-0.5 rounded">onActivate</code> for accessibility.
              </p>
              {activeCardAction && (
                <p className="text-xs font-semibold text-paytm-navy mt-2">
                  ✓ {activeCardAction}
                </p>
              )}
            </div>
          </Card>

          <div className="bg-surface-card rounded-card border border-surface-border p-4 shadow-sm space-y-1">
            <h3 className="text-sm font-semibold text-ink-primary mb-2">ListRow Examples</h3>
            <ListRow
              title="Daily UPI Settlement"
              subtitle="Batch ref: BATCH_20261112_01"
              amount="₹9,000.00"
              onActivate={() => showToast('info', 'Row Clicked', 'Opened settlement batch details')}
            />
            <ListRow
              title="Disputed Settlement Deficit"
              subtitle="Pending bank re-sync"
              amount="₹6,000.00"
              onActivate={() => showToast('warning', 'Row Clicked', 'Opened discrepancy case')}
            />
            <ListRow
              title="QR Soundbox Subscription"
              subtitle="Monthly device fee"
              amount="₹125.00"
            />
          </div>
        </div>
      </section>

      {/* 3. Status Chips & Provenance Badges */}
      <section className="space-y-4">
        <div className="border-b border-surface-divider pb-2">
          <h2 className="text-lg font-semibold text-paytm-navy">3. Status Chips & Provenance Badges</h2>
          <p className="text-xs text-ink-secondary">Semantic lifecycle states and honest data provenance.</p>
        </div>

        <Card title="Case Status Chips">
          <div className="flex flex-wrap gap-2.5 pt-2">
            {allStatuses.map((st) => (
              <StatusChip key={st} status={st} />
            ))}
          </div>
        </Card>

        <Card title="Data Provenance Badges (SourceBadge)">
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <SourceBadge source="PAYTM_STAGING" size="md" />
            <SourceBadge source="SYNTHETIC_DEMO" size="md" />
            <SourceBadge source="MOCK_SETTLEMENT_OPS" size="md" />
            <SourceBadge source="INTEGRATION_UNAVAILABLE" size="md" />
          </div>
        </Card>
      </section>

      {/* 4. Overlays & Dialogs (Modal & Toast) */}
      <section className="space-y-4">
        <div className="border-b border-surface-divider pb-2">
          <h2 className="text-lg font-semibold text-paytm-navy">4. Overlays & Feedback Primitives</h2>
          <p className="text-xs text-ink-secondary">Accessible modals, toast notifications, and error containers.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card title="Modal Dialog">
            <p className="text-sm text-ink-secondary mb-4 pt-1">
              Supports backdrop dismissal, keyboard Esc handler, focus trapping, and tokenized footer actions.
            </p>
            <Button variant="primary" onClick={() => setIsModalOpen(true)}>
              Open Demo Modal
            </Button>
          </Card>

          <Card title="Toast Notification Triggers">
            <p className="text-sm text-ink-secondary mb-3 pt-1">
              Auto-dismissing alerts with semantic icons and status tokens.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                className="text-xs min-h-10 px-3"
                onClick={() => showToast('success', 'Payment Received', '₹15,000.00 credited to account.')}
              >
                Success Toast
              </Button>
              <Button
                variant="secondary"
                className="text-xs min-h-10 px-3"
                onClick={() => showToast('warning', 'Approval Required', 'Re-sync needs supervisor authorization.')}
              >
                Warning Toast
              </Button>
              <Button
                variant="secondary"
                className="text-xs min-h-10 px-3"
                onClick={() => showToast('error', 'Reconciliation Failure', 'Bank ledger hash mismatch.')}
              >
                Error Toast
              </Button>
              <Button
                variant="secondary"
                className="text-xs min-h-10 px-3"
                onClick={() => showToast('info', 'Cascade Active', 'Ollama local fallback enabled.')}
              >
                Info Toast
              </Button>
            </div>
          </Card>
        </div>
      </section>

      {/* 5. States & Placeholders (Skeleton, Empty, Error) */}
      <section className="space-y-4">
        <div className="border-b border-surface-divider pb-2">
          <h2 className="text-lg font-semibold text-paytm-navy">5. State Containers & Placeholders</h2>
          <p className="text-xs text-ink-secondary">Calm motion pulse skeletons, empty states, and collapsible errors.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card title="Skeleton Loading">
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-3">
                <Skeleton variant="circular" width="40px" height="40px" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton variant="text" width="60%" />
                  <Skeleton variant="text" width="40%" />
                </div>
              </div>
              <Skeleton variant="rectangular" height="72px" />
            </div>
          </Card>

          <EmptyState
            title="No Pending Disputes"
            description="All settlement batches for this merchant are balanced and verified."
            action={
              <Button
                variant="secondary"
                className="text-xs min-h-10 px-3"
                onClick={() => showToast('info', 'Refresh', 'Checking latest settlement batches')}
              >
                Check Again
              </Button>
            }
          />

          <ErrorState
            title="Gateway Timeout"
            message="Settlement verification service failed to respond within 5000ms."
            details="Trace ID: tr-99201\nError: 504 Gateway Timeout on /api/v1/settlements/verify"
            onRetry={() => showToast('info', 'Retrying', 'Sending request again...')}
          />
        </div>
      </section>

      {/* Demo Modal Instance */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Approve Settlement Re-Sync"
        subtitle="Supervisor authorization step (Two-key discipline)"
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                setIsModalOpen(false)
                showToast('success', 'Authorized', 'Settlement re-sync approved and queued.')
              }}
            >
              Confirm Approval
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="p-3 bg-surface-subtle rounded-lg border border-surface-border">
            <div className="flex justify-between text-xs text-ink-secondary">
              <span>Discrepancy Amount:</span>
              <span className="font-semibold text-paytm-navy">₹6,000.00</span>
            </div>
            <div className="flex justify-between text-xs text-ink-secondary mt-1">
              <span>Merchant:</span>
              <span className="font-medium text-ink-primary">Sharma General Store</span>
            </div>
          </div>
          <p className="text-xs text-ink-secondary">
            Approving this action triggers an automated credit correction to the merchant's settlement ledger following cryptographic verification.
          </p>
        </div>
      </Modal>

      {/* Toast Portal Container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        <div className="pointer-events-auto">
          <Toast
            isOpen={toastState.isOpen}
            onClose={() => setToastState((prev) => ({ ...prev, isOpen: false }))}
            variant={toastState.variant}
            title={toastState.title}
            message={toastState.message}
          />
        </div>
      </div>
    </div>
  )
}
