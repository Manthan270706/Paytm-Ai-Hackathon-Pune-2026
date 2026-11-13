import { FC } from 'react'
import { UserRole } from '../types/api'
import { Languages, Shield, User, RotateCcw } from 'lucide-react'

interface HeaderProps {
  currentRole: UserRole
  onRoleChange: (role: UserRole) => void
  currentLanguage: string
  onLanguageChange: (lang: string) => void
  onResetDemo: () => void
  isResetting: boolean
}

export const Header: FC<HeaderProps> = ({
  currentRole,
  onRoleChange,
  currentLanguage,
  onLanguageChange,
  onResetDemo,
  isResetting,
}) => {
  return (
    <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo and Brand */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-sky-600 to-cyan-400 flex items-center justify-center font-black text-slate-950 text-xl shadow-lg shadow-sky-500/20">
            ₹
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-white tracking-tight">OpsSaathi AI</span>
              <span className="text-[10px] font-semibold uppercase bg-sky-500/10 text-sky-400 border border-sky-500/20 px-2 py-0.5 rounded-full">
                Track 3
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">Autonomous Merchant Operations Teammate</p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          {/* Language Selector */}
          <div className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200">
            <Languages className="h-3.5 w-3.5 text-sky-400" />
            <select
              value={currentLanguage}
              onChange={(e) => onLanguageChange(e.target.value)}
              className="bg-transparent text-slate-200 outline-none cursor-pointer font-medium pr-1"
            >
              <option value="en" className="bg-slate-800 text-slate-200">English</option>
              <option value="hi" className="bg-slate-800 text-slate-200">हिन्दी (Hindi)</option>
              <option value="mr" className="bg-slate-800 text-slate-200">मराठी (Marathi)</option>
            </select>
          </div>

          {/* Reset Demo Button */}
          <button
            onClick={onResetDemo}
            disabled={isResetting}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700/80 text-amber-400 border border-amber-500/30 rounded-lg px-3 py-1.5 text-xs font-medium transition shadow-sm disabled:opacity-50"
            title="Reset to frozen scenario (₹15,000 expected, ₹9,000 observed)"
          >
            <RotateCcw className={`h-3.5 w-3.5 ${isResetting ? 'animate-spin' : ''}`} />
            <span>{isResetting ? 'Resetting...' : 'Reset Demo'}</span>
          </button>

          {/* Role Toggle / Demo Login */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-medium">
            <button
              onClick={() => onRoleChange('MERCHANT')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
                currentRole === 'MERCHANT'
                  ? 'bg-sky-500 text-slate-950 font-semibold shadow-md shadow-sky-500/20'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <User className="h-3.5 w-3.5" />
              <span>Merchant View</span>
            </button>
            <button
              onClick={() => onRoleChange('SUPPORT_AGENT')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
                currentRole === 'SUPPORT_AGENT'
                  ? 'bg-purple-500 text-white font-semibold shadow-md shadow-purple-500/20'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Shield className="h-3.5 w-3.5" />
              <span>Ops Console</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
