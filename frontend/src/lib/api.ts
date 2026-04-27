function resolveApiBase() {
  const configured = import.meta.env.VITE_API_BASE?.trim()
  if (configured) {
    if (configured.startsWith('http://') || configured.startsWith('https://')) {
      return configured.replace(/\/$/, '')
    }
    if (typeof window !== 'undefined') {
      return new URL(configured, window.location.origin).toString().replace(/\/$/, '')
    }
  }

  if (typeof window !== 'undefined') {
    return new URL('/api/v1', window.location.origin).toString().replace(/\/$/, '')
  }

  return 'http://127.0.0.1:8000/api/v1'
}

const API_BASE = resolveApiBase()
export const BACKEND_ORIGIN = new URL(API_BASE).origin

export function toBackendUrl(path: string | null | undefined): string | undefined {
  if (!path) {
    return undefined
  }
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  return `${BACKEND_ORIGIN}${path}`
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(await buildErrorMessage(response, 'GET', path))
  }
  return response.json() as Promise<T>
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(await buildErrorMessage(response, 'POST', path))
  }
  return response.json() as Promise<T>
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(await buildErrorMessage(response, 'DELETE', path))
  }
  return response.json() as Promise<T>
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(await buildErrorMessage(response, 'PUT', path))
  }
  return response.json() as Promise<T>
}

async function buildErrorMessage(response: Response, method: string, path: string) {
  let detail = ''

  try {
    const contentType = response.headers.get('content-type') ?? ''
    if (contentType.includes('application/json')) {
      const payload = (await response.json()) as { detail?: string }
      detail = payload.detail ?? ''
    } else {
      detail = (await response.text()).trim()
    }
  } catch {
    detail = ''
  }

  return detail
    ? `${method} ${path} failed (${response.status}): ${detail}`
    : `${method} ${path} failed (${response.status})`
}
