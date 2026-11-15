import { FC } from 'react'
import { UserRole } from '../types/api'
import { Languages, Shield, User, RotateCcw, Activity, LayoutGrid } from 'lucide-react'

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
    <header className="sticky top-0 z-50 bg-paytm-navy text-white border-b border-paytm-navy-dark shadow-sm font-sans">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo and Brand */}
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-paytm-cyan text-paytm-navy flex items-center justify-center font-black text-lg shadow-xs">
            ₹
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base text-white tracking-tight">OpsSaathi AI</span>
              <span className="text-[10px] font-semibold uppercase bg-paytm-cyan/20 text-paytm-cyan border border-paytm-cyan/30 px-1.5 py-0.2 rounded">
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
            <p className="text-[11px] text-white/70">Settlement Resolution Teammate</p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Language Selector */}
          <div className="flex items-center gap-1.5 bg-paytm-navy-light border border-white/20 rounded-lg px-2.5 py-1.5 text-xs text-white">
            <Languages className="h-3.5 w-3.5 text-paytm-cyan" />
            <select
              value={currentLanguage}
              onChange={(e) => onLanguageChange(e.target.value)}
              className="bg-transparent text-white outline-none cursor-pointer font-medium pr-1"
            >
              <option value="en" className="bg-paytm-navy text-white">English</option>
              <option value="hi" className="bg-paytm-navy text-white">हिन्दी (Hindi)</option>
              <option value="mr" className="bg-paytm-navy text-white">मराठी (Marathi)</option>
            </select>
          </div>

          {/* Reset Demo Button */}
          <button
            type="button"
            onClick={onResetDemo}
            disabled={isResetting}
            className="flex items-center gap-1.5 bg-paytm-navy-light hover:bg-paytm-navy-dark text-white border border-white/20 rounded-lg px-2.5 py-1.5 text-xs font-medium transition shadow-xs disabled:opacity-50"
            title="Reset to frozen baseline scenario (₹15,000 expected, ₹9,000 observed)"
          >
            <RotateCcw className={`h-3.5 w-3.5 text-paytm-cyan ${isResetting ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{isResetting ? 'Resetting...' : 'Reset'}</span>
          </button>

          {/* Integration Health Button */}
          {onOpenHealth && (
            <button
              type="button"
              onClick={onOpenHealth}
              className="flex items-center gap-1.5 bg-paytm-navy-light hover:bg-paytm-navy-dark text-paytm-cyan border border-paytm-cyan/30 rounded-lg px-2.5 py-1.5 text-xs font-medium transition shadow-xs"
              title="View active provider adapters and integration health"
            >
              <Activity className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Health</span>
            </button>
          )}

          {/* Design Catalog Button */}
          {onOpenCatalog && (
            <button
              type="button"
              onClick={onOpenCatalog}
              className="flex items-center gap-1.5 bg-paytm-navy-light hover:bg-paytm-navy-dark text-white border border-white/20 rounded-lg px-2.5 py-1.5 text-xs font-medium transition shadow-xs"
              title="View design tokens and primitive UI components"
            >
              <LayoutGrid className="h-3.5 w-3.5 text-paytm-cyan" />
              <span className="hidden sm:inline">Catalog</span>
            </button>
          )}

          {/* Role Switcher */}
          <div className="flex items-center bg-paytm-navy-dark p-1 rounded-xl border border-white/10 text-xs font-medium">
            <button
              type="button"
              onClick={() => onRoleChange('MERCHANT')}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition ${
                currentRole === 'MERCHANT'
                  ? 'bg-paytm-cyan text-paytm-navy font-bold shadow-xs'
                  : 'text-white/70 hover:text-white'
              }`}
            >
              <User className="h-3.5 w-3.5" />
              <span className="hidden md:inline">Merchant</span>
            </button>
            <button
              type="button"
              onClick={() => onRoleChange('SUPPORT_AGENT')}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition ${
                currentRole === 'SUPPORT_AGENT'
                  ? 'bg-white text-paytm-navy font-bold shadow-xs'
                  : 'text-white/70 hover:text-white'
              }`}
            >
              <Shield className="h-3.5 w-3.5" />
              <span className="hidden md:inline">Console</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
