import React from 'react'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'danger'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'default', ...props }, ref) => {
    let baseClass = 'theme-toggle'
    if (variant === 'primary') baseClass += ' render-actions--primary'
    if (variant === 'danger') baseClass += ' render-actions--danger'

    return (
      <button
        ref={ref}
        className={`${baseClass} ${className}`.trim()}
        {...props}
      />
    )
  }
)

Button.displayName = 'Button'
