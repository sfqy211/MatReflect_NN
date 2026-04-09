import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { ErrorBoundary } from './components/ErrorBoundary'
import './styles.css'

const queryClient = new QueryClient()
const rootElement = document.getElementById('app')

function formatError(error: unknown) {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}${error.stack ? `\n\n${error.stack}` : ''}`
  }

  return String(error)
}

function renderBootstrapError(error: unknown) {
  if (!rootElement) {
    console.error('MatReflect_NN bootstrap failed before #app was found', error)
    return
  }

  rootElement.innerHTML = `
    <div style="min-height: 100vh; padding: 24px; background: #111827; color: #f3f4f6; font-family: Consolas, 'Courier New', monospace;">
      <h1 style="margin: 0 0 16px; font-size: 20px;">Frontend bootstrap failed</h1>
      <pre style="margin: 0; white-space: pre-wrap; word-break: break-word;">${formatError(error)}</pre>
    </div>
  `
}

window.addEventListener('error', (event) => {
  console.error('Unhandled window error', event.error ?? event.message)
})

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection', event.reason)
})

async function bootstrap() {
  if (!rootElement) {
    throw new Error('Unable to find #app root element')
  }

  rootElement.setAttribute('data-bootstrap', 'loading')

  const { App } = await import('./App')

  rootElement.setAttribute('data-bootstrap', 'ready')

  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </ErrorBoundary>
    </React.StrictMode>,
  )
}

void bootstrap().catch((error) => {
  renderBootstrapError(error)
})
