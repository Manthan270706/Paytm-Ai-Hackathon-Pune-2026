import { FC } from 'react'
import { UserRole } from '../types/api'
import { Languages, Shield, User, RotateCcw, Activity, LayoutGrid } from 'lucide-react'
import { PaytmLogo } from './PaytmLogo'

interface HeaderProps {
  currentRole: UserRole
  onRoleChange: (role: UserRole) => void
  currentLanguage: string
  onLanguageChange: (lang: string) => void
  onResetDemo: () => void
  isResetting: boolean
  isReplayMode?: boolean
  onOpenHealth?: () => void
  onOpenCatalog?: () => void
}

export const Header: FC<HeaderProps> = ({
  currentRole,
  onRoleChange,
  currentLanguage,
  onLanguageChange,
  onResetDemo,
  isResetting,
  isReplayMode = false,
  onOpenHealth,
  onOpenCatalog,
}) => {
  return (
    <header className="sticky top-0 z-50 bg-white text-ink-primary border-b border-surface-divider shadow-[0_2px_10px_rgba(0,0,0,0.03)] font-sans">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Official Paytm Logo and Brand */}
        <div className="flex items-center gap-3">
          <PaytmLogo height={26} showUpi={true} />

          <span className="h-5 w-px bg-surface-border mx-0.5 hidden sm:block" />

          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm sm:text-base text-paytm-navy tracking-tight">OpsSaathi AI</span>
              <span className="text-[10px] font-bold uppercase bg-paytm-cyan text-white px-2 py-0.5 rounded-full shadow-xs tracking-wide">
                Pi Agent
              </span>
              <span className="text-[10px] font-semibold uppercase bg-paytm-cyan/15 text-paytm-navy border border-paytm-cyan/30 px-1.5 py-0.2 rounded hidden md:inline">
                Track 3
              </span>
              {isReplayMode && (
                <span
                  className="text-[10px] font-medium bg-status-approval-bg text-status-approval-text border border-status-approval-border px-1.5 py-0.2 rounded-full flex items-center gap-1 shadow-xs"
                  title="Serving deterministic cached golden scenario (PRD §12.3 Replay Mode)"
                >
                  <RotateCcw className="h-2.5 w-2.5 animate-spin" />
                  Replay
                </span>
              )}
            </div>
            <p className="text-[10px] sm:text-[11px] text-ink-secondary">Autonomous Merchant Operations Teammate</p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Language Selector */}
          <div className="flex items-center gap-1.5 bg-surface-subtle border border-surface-border rounded-full px-2.5 py-1 text-xs text-ink-primary">
            <Languages className="h-3.5 w-3.5 text-paytm-cyan" />
            <select
              value={currentLanguage}
              onChange={(e) => onLanguageChange(e.target.value)}
              className="bg-transparent text-ink-primary outline-none cursor-pointer font-medium pr-1 text-xs"
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी (Hindi)</option>
              <option value="mr">मराठी (Marathi)</option>
            </select>
          </div>

          {/* Reset Demo Button */}
          <button
            type="button"
            onClick={onResetDemo}
            disabled={isResetting}
            className="flex items-center gap-1.5 bg-surface-subtle hover:bg-surface-border text-ink-secondary hover:text-paytm-navy border border-surface-border rounded-full px-2.5 py-1 text-xs font-medium transition shadow-xs disabled:opacity-50"
            title="Reset to frozen baseline scenario (₹15,000 expected, ₹9,000 observed)"
          >
            <RotateCcw className={`h-3.5 w-3.5 text-paytm-navy ${isResetting ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{isResetting ? 'Resetting...' : 'Reset'}</span>
          </button>

          {/* Integration Health Button */}
          {onOpenHealth && (
            <button
              type="button"
              onClick={onOpenHealth}
              className="flex items-center gap-1.5 bg-surface-subtle hover:bg-surface-border text-paytm-navy border border-surface-border rounded-full px-2.5 py-1 text-xs font-medium transition shadow-xs"
              title="View active provider adapters and integration health"
            >
              <Activity className="h-3.5 w-3.5 text-paytm-cyan" />
              <span className="hidden sm:inline">Health</span>
            </button>
          )}

          {/* Design Catalog Button */}
          {onOpenCatalog && (
            <button
              type="button"
              onClick={onOpenCatalog}
              className="flex items-center gap-1.5 bg-surface-subtle hover:bg-surface-border text-ink-secondary hover:text-paytm-navy border border-surface-border rounded-full px-2.5 py-1 text-xs font-medium transition shadow-xs"
              title="View design tokens and primitive UI components"
            >
              <LayoutGrid className="h-3.5 w-3.5 text-paytm-cyan" />
              <span className="hidden sm:inline">Catalog</span>
            </button>
          )}

          {/* Official Paytm "Sign In" style Role Switcher */}
          <div className="flex items-center bg-surface-subtle p-0.5 rounded-full border border-surface-border text-xs font-medium">
            <button
              type="button"
              onClick={() => onRoleChange('MERCHANT')}
              className={`flex items-center gap-1.5 pl-1.5 pr-2.5 py-1 rounded-full transition ${
                currentRole === 'MERCHANT'
                  ? 'bg-paytm-navy text-white font-bold shadow-xs'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center ${currentRole === 'MERCHANT' ? 'bg-paytm-cyan text-white' : 'bg-surface-border text-ink-secondary'}`}>
                <User className="h-3 w-3" />
              </div>
              <span className="hidden md:inline">Merchant</span>
            </button>
            <button
              type="button"
              onClick={() => onRoleChange('SUPPORT_AGENT')}
              className={`flex items-center gap-1.5 pl-1.5 pr-2.5 py-1 rounded-full transition ${
                currentRole === 'SUPPORT_AGENT'
                  ? 'bg-paytm-navy text-white font-bold shadow-xs'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center ${currentRole === 'SUPPORT_AGENT' ? 'bg-paytm-cyan text-white' : 'bg-surface-border text-ink-secondary'}`}>
                <Shield className="h-3 w-3" />
              </div>
              <span className="hidden md:inline">Console</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
