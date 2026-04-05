type FeedbackTone = 'empty' | 'error' | 'info' | 'success'

type FeedbackPanelProps = {
  title: string
  message?: string
  tone?: FeedbackTone
  actionLabel?: string
  onAction?: () => void
  compact?: boolean
}

export function FeedbackPanel({
  title,
  message,
  tone = 'info',
  actionLabel,
  onAction,
  compact = false,
}: FeedbackPanelProps) {
  const className = compact
    ? `feedback-panel feedback-panel--${tone} feedback-panel--compact`
    : `feedback-panel feedback-panel--${tone}`

  return (
    <div className={className}>
      <strong>{title}</strong>
      {message ? <p>{message}</p> : null}
      {actionLabel && onAction ? (
        <div className="feedback-panel__actions">
          <button type="button" className="theme-toggle" onClick={onAction}>
            {actionLabel}
          </button>
        </div>
      ) : null}
    </div>
  )
}
