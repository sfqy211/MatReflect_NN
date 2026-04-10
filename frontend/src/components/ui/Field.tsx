import React from 'react'

export interface FieldProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  label: string
}

export const Field = React.forwardRef<HTMLLabelElement, FieldProps>(
  ({ className = '', label, children, ...props }, ref) => {
    return (
      <label ref={ref} className={`field ${className}`.trim()} {...props}>
        <span>{label}</span>
        {children}
      </label>
    )
  }
)

Field.displayName = 'Field'
