const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')
const DEV_USER_ID = import.meta.env.VITE_DEV_USER_ID || 'demo-student'
const DEV_EMAIL = import.meta.env.VITE_DEV_EMAIL || 'student@example.local'

type RequestOptions = RequestInit & { authToken?: string }

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('X-Dev-User-Id', DEV_USER_ID)
  headers.set('X-Dev-Email', DEV_EMAIL)
  if (options.authToken) headers.set('Authorization', `Bearer ${options.authToken}`)

  const isFormData = options.body instanceof FormData
  if (options.body && !isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  } catch {
    throw new Error('Cannot reach the backend. Confirm FastAPI is running at http://127.0.0.1:8000.')
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const data = await response.json()
      message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail ?? data)
    } catch {
      message = response.statusText || message
    }
    throw new Error(message)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T,>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T,>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T,>(path: string, body: FormData) => request<T>(path, { method: 'POST', body }),
  async download(path: string, filename: string) {
    const headers = new Headers({ 'X-Dev-User-Id': DEV_USER_ID, 'X-Dev-Email': DEV_EMAIL })
    const response = await fetch(`${API_BASE_URL}${path}`, { headers })
    if (!response.ok) throw new Error(`Download failed (${response.status})`)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  },
}

export const apiRoot = API_BASE_URL.replace(/\/api\/v1\/?$/, '')
