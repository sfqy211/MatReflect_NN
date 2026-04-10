import React from 'react'

export interface CheckboxFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string
}

export const CheckboxField = React.forwardRef<HTMLInputElement, CheckboxFieldProps>(
  ({ className = '', label, ...props }, ref) => {
    return (
      <label className={`toggle-field ${className}`.trim()}>
        <input type="checkbox" ref={ref} {...props} />
        <span>{label}</span>
      </label>
    )
  }
)

CheckboxField.displayName = 'CheckboxField'
