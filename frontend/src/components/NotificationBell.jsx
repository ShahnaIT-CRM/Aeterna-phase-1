import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'

const ago = (iso) => {
  const s = Math.max(1, Math.round((Date.now() - new Date(iso)) / 1000))
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}

/** Bell with an unread count and a dropdown of the latest notifications. Polls once a minute. */
export default function NotificationBell() {
  const [data, setData] = useState({ unread_count: 0, results: [] })
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  const nav = useNavigate()

  const load = useCallback(() => api.get('/notifications/').then((r) => setData(r.data)).catch(() => {}), [])
  useEffect(() => {
    load()
    const t = setInterval(() => !document.hidden && load(), 60000)
    return () => clearInterval(t)
  }, [load])

  useEffect(() => {
    if (!open) return
    const away = (e) => !box.current?.contains(e.target) && setOpen(false)
    const esc = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc) }
  }, [open])

  const toggle = () => { setOpen((o) => !o); if (!open) load() }
  const go = async (n) => {
    setOpen(false)
    if (!n.is_read) {
      setData((d) => ({ unread_count: Math.max(0, d.unread_count - 1), results: d.results.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)) }))
      api.post(`/notifications/${n.id}/read/`).catch(() => {})
    }
    if (n.link) nav(n.link)
  }
  const readAll = async () => {
    await api.post('/notifications/read-all/')
    setData((d) => ({ unread_count: 0, results: d.results.map((x) => ({ ...x, is_read: true })) }))
  }

  return (
    <div className="relative" ref={box}>
      <button
        type="button" onClick={toggle} aria-haspopup="true" aria-expanded={open}
        aria-label={`Notifications${data.unread_count ? `, ${data.unread_count} unread` : ''}`}
        className="relative rounded-full p-2 text-teal transition hover:bg-beige-dark"
      >
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M6 9a6 6 0 1112 0c0 5 2 6.5 2 6.5H4S6 14 6 9z" /><path d="M10 19a2 2 0 004 0" />
        </svg>
        {data.unread_count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
            {data.unread_count > 9 ? '9+' : data.unread_count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 max-w-[90vw] overflow-hidden rounded-lg border border-beige-line bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-beige-line px-4 py-2">
            <h2 className="text-sm font-bold">Notifications</h2>
            {data.unread_count > 0 && <button className="text-xs font-semibold underline" onClick={readAll}>Mark all read</button>}
          </div>
          {data.results.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-teal-soft">You're all caught up.</p>
          ) : (
            <ul className="max-h-96 divide-y divide-beige-line overflow-auto">
              {data.results.map((n) => (
                <li key={n.id}>
                  <button onClick={() => go(n)} className={`flex w-full gap-3 px-4 py-3 text-left transition hover:bg-beige ${n.is_read ? '' : 'bg-beige/60'}`}>
                    <span aria-hidden="true" className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.is_read ? 'bg-transparent' : 'bg-teal-light'}`} />
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold">{n.title}</span>
                      {n.body && <span className="block text-xs text-teal-soft">{n.body}</span>}
                      <span className="mt-0.5 block text-[11px] text-teal-soft/80">{ago(n.created_at)}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
