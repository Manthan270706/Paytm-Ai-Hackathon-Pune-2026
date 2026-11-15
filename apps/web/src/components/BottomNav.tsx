import { FC } from 'react'
import { Home, Receipt, Layers, HelpCircle } from 'lucide-react'

export type MerchantTab = 'home' | 'payments' | 'settlements' | 'help'

interface NavItem {
  id: MerchantTab
  label: string
  icon: FC<{ className?: string }>
  badge?: number | string
}

interface BottomNavProps {
  activeTab: MerchantTab
  onSelectTab: (tab: MerchantTab) => void
  badgeCounts?: Partial<Record<MerchantTab, number | string>>
  className?: string
  testId?: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'payments', label: 'Payments', icon: Receipt },
  { id: 'settlements', label: 'Settlements', icon: Layers },
  { id: 'help', label: 'Help & Chat', icon: HelpCircle },
]

export const BottomNav: FC<BottomNavProps> = ({
  activeTab,
  onSelectTab,
  badgeCounts = {},
  className = '',
  testId = 'bottom-nav',
}) => {
  return (
    <nav
      data-testid={testId}
      aria-label="Merchant mobile navigation"
      className={`fixed bottom-0 left-0 right-0 z-40 bg-surface-card border-t border-surface-border shadow-lg font-sans ${className}`}
    >
      <div className="max-w-md mx-auto px-2 flex items-center justify-around h-16">
        {NAV_ITEMS.map((item) => {
          const isActive = activeTab === item.id
          const Icon = item.icon
          const badge = badgeCounts[item.id]

          return (
            <button
              key={item.id}
              type="button"
              data-testid={`${testId}-${item.id}`}
              onClick={() => onSelectTab(item.id)}
              aria-selected={isActive}
              className={`flex-1 flex flex-col items-center justify-center min-h-12 py-1 px-2 rounded-lg transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-paytm-cyan ${
                isActive
                  ? 'text-paytm-navy font-semibold'
                  : 'text-ink-secondary hover:text-ink-primary font-normal'
              }`}
            >
              <div className="relative">
                <Icon
                  className={`w-5 h-5 transition-transform ${
                    isActive ? 'scale-110 text-paytm-navy stroke-[2.2]' : 'text-ink-secondary'
                  }`}
                />
                {badge !== undefined && (
                  <span className="absolute -top-1.5 -right-2.5 min-w-4 h-4 px-1 rounded-full text-[10px] font-bold bg-paytm-cyan text-paytm-navy flex items-center justify-center shadow-xs">
                    {badge}
                  </span>
                )}
              </div>
              <span className={`text-[11px] mt-1 ${isActive ? 'font-semibold text-paytm-navy' : 'text-ink-secondary'}`}>
                {item.label}
              </span>
              {isActive && (
                <span className="w-4 h-0.5 rounded-full bg-paytm-cyan mt-0.5" />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
