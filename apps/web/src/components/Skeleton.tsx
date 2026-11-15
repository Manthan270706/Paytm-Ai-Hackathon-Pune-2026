import { FC } from 'react'

interface SkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string
  height?: string
  className?: string
  count?: number
  testId?: string
}

export const Skeleton: FC<SkeletonProps> = ({
  variant = 'text',
  width = '100%',
  height,
  className = '',
  count = 1,
  testId = 'skeleton',
}) => {
  const getDefaultHeight = () => {
    switch (variant) {
      case 'circular':
        return width || '40px'
      case 'rectangular':
        return height || '120px'
      case 'text':
      default:
        return height || '16px'
    }
  }

  const getBorderRadius = () => {
    switch (variant) {
      case 'circular':
        return 'rounded-full'
      case 'rectangular':
        return 'rounded-xl'
      case 'text':
      default:
        return 'rounded-md'
    }
  }

  const items = Array.from({ length: count }, (_, i) => i)

  return (
    <div className="flex flex-col gap-2 w-full" data-testid={testId}>
      {items.map((key) => (
        <div
          key={key}
          style={{ width, height: getDefaultHeight() }}
          className={`bg-surface-subtle animate-pulse ${getBorderRadius()} ${className}`}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}
