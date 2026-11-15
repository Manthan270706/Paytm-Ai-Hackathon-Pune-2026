import React from 'react'

interface PaytmLogoProps {
  className?: string
  height?: number
  showUpi?: boolean
}

export const PaytmLogo: React.FC<PaytmLogoProps> = ({
  className = '',
  height = 28,
  showUpi = true,
}) => {
  return (
    <div className={`inline-flex items-center gap-1.5 select-none ${className}`}>
      {/* Official Paytm Wordmark */}
      <div className="flex items-baseline font-black tracking-tighter" style={{ fontSize: `${height}px`, lineHeight: 1 }}>
        <span style={{ color: '#002970' }} className="font-extrabold">pay</span>
        <span style={{ color: '#00BAF2' }} className="font-extrabold">tm</span>
      </div>

      {showUpi && (
        <div className="flex items-center gap-1 ml-0.5">
          {/* Heart icon */}
          <svg className="w-3.5 h-3.5 text-[#EA3B52] fill-current" viewBox="0 0 24 24">
            <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
          </svg>
          <span className="font-black italic text-[#002970] text-[11px] tracking-tight">
            UPI
          </span>
        </div>
      )}
    </div>
  )
}
