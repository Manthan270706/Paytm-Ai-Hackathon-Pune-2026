import { FC } from 'react'
import {
  Inbox,
  CheckSquare,
  BarChart3,
  FileText,
  Activity,
  LayoutGrid,
  Shield,
} from 'lucide-react'

export type OpsNavView = 'queue' | 'approvals' | 'metrics' | 'audit' | 'health' | 'catalog'

interface NavOption {
  id: OpsNavView
  label: string
  icon: FC<{ className?: string }>
  badge?: number | string
}

interface SidebarProps {
  activeView: OpsNavView
  onSelectView: (view: OpsNavView) => void
  badgeCounts?: Partial<Record<OpsNavView, number | string>>
  agentName?: string
  agentRole?: string
  className?: string
  testId?: string
}

const NAV_OPTIONS: NavOption[] = [
  { id: 'queue', label: 'Dispute Queue', icon: Inbox },
  { id: 'approvals', label: 'Pending Approvals', icon: CheckSquare },
  { id: 'metrics', label: 'Outcome Metrics', icon: BarChart3 },
  { id: 'audit', label: 'Audit & Provenance', icon: FileText },
  { id: 'health', label: 'Integration Health', icon: Activity },
  { id: 'catalog', label: 'Component Gallery', icon: LayoutGrid },
]

export const Sidebar: FC<SidebarProps> = ({
  activeView,
  onSelectView,
  badgeCounts = {},
  agentName = 'Ops Supervisor',
  agentRole = 'Support Agent',
  className = '',
  testId = 'ops-sidebar',
}) => {
  return (
    <aside
      data-testid={testId}
      aria-label="Operations console navigation"
      className={`w-64 flex-shrink-0 bg-surface-card border-r border-surface-border flex flex-col justify-between p-4 font-sans ${className}`}
    >
      <div>
        {/* Brand header */}
        <div className="flex items-center gap-3 px-2 py-3 border-b border-surface-divider mb-4">
          <div className="w-9 h-9 rounded-xl bg-paytm-navy text-white flex items-center justify-center font-bold text-base shadow-sm">
            ₹
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-sm text-paytm-navy tracking-tight">OpsSaathi AI</span>
              <span className="text-[10px] font-semibold uppercase bg-paytm-cyan-light text-paytm-navy border border-paytm-cyan/30 px-1.5 py-0.2 rounded">
                Console
              </span>
            </div>
            <p className="text-[11px] text-ink-muted">Settlement Resolution Center</p>
          </div>
        </div>

        {/* Navigation list */}
        <nav className="space-y-1">
          {NAV_OPTIONS.map((item) => {
            const isActive = activeView === item.id
            const Icon = item.icon
            const badge = badgeCounts[item.id]

            return (
              <button
                key={item.id}
                type="button"
                data-testid={`${testId}-${item.id}`}
                onClick={() => onSelectView(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`w-full flex items-center justify-between min-h-12 px-3 py-2.5 rounded-lg text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan ${
                  isActive
                    ? 'bg-paytm-navy text-white shadow-xs'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-surface-subtle'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-paytm-cyan' : 'text-ink-secondary'}`} />
                  <span>{item.label}</span>
                </div>
                {badge !== undefined && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                      isActive
                        ? 'bg-paytm-cyan text-paytm-navy'
                        : 'bg-surface-subtle text-ink-primary border border-surface-border'
                    }`}
                  >
                    {badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Footer Profile */}
      <div className="p-3 bg-surface-subtle rounded-xl border border-surface-border flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-paytm-navy/10 text-paytm-navy flex items-center justify-center font-bold text-xs">
          <Shield className="w-4 h-4 text-paytm-navy" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-ink-primary truncate">{agentName}</p>
          <p className="text-[10px] text-ink-muted truncate">{agentRole}</p>
        </div>
      </div>
    </aside>
  )
}
