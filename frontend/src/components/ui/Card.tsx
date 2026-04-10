import React from 'react'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'surface' | 'metric' | 'settings' | 'empty' | 'status' | 'detail' | 'pipeline'
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', variant = 'surface', ...props }, ref) => {
    let baseClass = ''
    switch (variant) {
      case 'surface':
        baseClass = 'surface-card'
        break
      case 'metric':
        baseClass = 'metric-card'
        break
      case 'settings':
        baseClass = 'settings-card'
        break
      case 'empty':
        baseClass = 'empty-card'
        break
      case 'status':
        baseClass = 'status-metric'
        break
      case 'detail':
        baseClass = 'detail-board'
        break
      case 'pipeline':
        baseClass = 'pipeline-card'
        break
      default:
        baseClass = 'surface-card'
    }

    return (
      <div
        ref={ref}
        className={`${baseClass} ${className}`.trim()}
        {...props}
      />
    )
  }
)

Card.displayName = 'Card'
