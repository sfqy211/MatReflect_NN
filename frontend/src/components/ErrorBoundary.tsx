import { Component, type ReactNode } from 'react'

type ErrorBoundaryProps = {
  children: ReactNode
}

type ErrorBoundaryState = {
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    error: null,
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, errorInfo: unknown) {
    console.error('Unhandled frontend error', error, errorInfo)
  }

  reset = () => {
    this.setState({ error: null })
  }

  render() {
    if (this.state.error) {
      return (
        <div className="app-shell">
          <section className="workspace-canvas">
            <div className="feedback-panel feedback-panel--error feedback-panel--hero">
              <strong>前端发生未捕获错误</strong>
              <p>{this.state.error.message || '组件树在渲染过程中发生异常。'}</p>
              <div className="feedback-panel__actions">
                <button type="button" className="theme-toggle" onClick={this.reset}>
                  重试渲染
                </button>
                <button type="button" className="theme-toggle" onClick={() => window.location.reload()}>
                  刷新页面
                </button>
              </div>
            </div>
          </section>
        </div>
      )
    }

    return this.props.children
  }
}
