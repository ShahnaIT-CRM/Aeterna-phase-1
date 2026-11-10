import { useState } from 'react'
import api, { errMsg } from '../api'
import { Alert } from './ui'

export const linkedInShareUrl = (url) => `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`

/** Public link controls. The page only works once the teacher has chosen to make the profile Public. */
export default function ShareProfile({ teacherId, visibility, onVisibility }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [copied, setCopied] = useState(false)
  const url = `${window.location.origin}/t/${teacherId}`

  const makePublic = async () => {
    setBusy(true)
    setErr('')
    try {
      await api.patch('/teacher/profile/', { visibility: 'public' })
      onVisibility('public')
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(false)
    }
  }
  const copy = async () => {
    try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000) } catch { window.prompt('Copy this link', url) }
  }

  return (
    <section className="card" aria-labelledby="share-h">
      <h2 id="share-h" className="text-xl font-bold">Your public certificate</h2>
      {visibility !== 'public' ? (
        <div className="mt-2 space-y-3 text-sm">
          <p className="text-teal-soft">Share a verifiable page with your tier and signed degrees. It never shows your phone, email, address, date of birth, marks or documents. Your profile is not public right now.</p>
          <button className="btn" onClick={makePublic} disabled={busy}>{busy ? 'Updating…' : 'Make my profile public'}</button>
          <Alert>{err}</Alert>
        </div>
      ) : (
        <div className="mt-2 space-y-3 text-sm">
          <input readOnly aria-label="Public profile link" className="input font-mono text-xs" value={url} onFocus={(e) => e.target.select()} />
          <div className="flex flex-wrap gap-3">
            <a className="btn" href={linkedInShareUrl(url)} target="_blank" rel="noreferrer">Share to LinkedIn</a>
            <button className="btn-outline" onClick={copy}>{copied ? 'Copied ✓' : 'Copy link'}</button>
            <a className="btn-outline" href={`/t/${teacherId}`} target="_blank" rel="noreferrer">View page</a>
          </div>
        </div>
      )}
    </section>
  )
}
