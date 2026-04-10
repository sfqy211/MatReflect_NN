import React from 'react'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'chip' | 'detail' | 'tag' | 'gallery'
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className = '', variant = 'chip', ...props }, ref) => {
    let baseClass = ''
    switch (variant) {
      case 'chip':
        baseClass = 'chip'
        break
      case 'detail':
        baseClass = 'detail-pill'
        break
      case 'tag':
        baseClass = 'tag-chip'
        break
      case 'gallery':
        baseClass = 'gallery-count'
        break
      default:
        baseClass = 'chip'
    }

    return (
      <span
        ref={ref}
        className={`${baseClass} ${className}`.trim()}
        {...props}
      />
    )
  }
)

Badge.displayName = 'Badge'
