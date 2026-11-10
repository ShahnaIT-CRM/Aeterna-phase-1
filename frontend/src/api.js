import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// For public pages (/t/:id): never sends a token, so a stale login can not trigger the redirect-to-login logic below.
export const publicApi = axios.create({ baseURL: '/api' })

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('access')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

let refreshing = null
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config
    const refresh = localStorage.getItem('refresh')
    if (err.response?.status === 401 && refresh && !orig._retry && !orig.url.startsWith('/auth/')) {
      orig._retry = true
      try {
        refreshing = refreshing || axios.post('/api/auth/refresh/', { refresh })
        const { data } = await refreshing
        localStorage.setItem('access', data.access)
        return api(orig)
      } catch {
        localStorage.clear()
        window.location.href = '/auth'
      } finally {
        refreshing = null
      }
    }
    return Promise.reject(err)
  }
)

// Turn a DRF error response into one readable string.
export function errMsg(e) {
  const d = e?.response?.data
  if (!d) return 'Could not reach the server. Check your connection and try again.'
  if (typeof d === 'string') return 'Something went wrong on the server. Try again.'
  const flat = (v) => (Array.isArray(v) ? v.map(flat).join(' ') : typeof v === 'object' ? Object.values(v).map(flat).join(' ') : String(v))
  return Object.entries(d)
    .map(([k, v]) => (['detail', 'non_field_errors'].includes(k) ? flat(v) : `${k.replace(/_/g, ' ')}: ${flat(v)}`))
    .join(' | ')
}

export default api
