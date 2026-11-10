import { useCallback, useEffect, useState } from 'react'
import api, { errMsg } from '../api'
import VerificationBadge from '../components/VerificationBadge'
import { Alert, Chip } from '../components/ui'

const short = (h = '', n = 10) => (h.length > n * 2 ? `${h.slice(0, n)}…${h.slice(-n)}` : h)
const when = (d) => (d ? new Date(d).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '')

/** Shows one of the teacher's uploads. Fetched with the login token, so the file is never an open link. */
function DocumentViewer({ requestId, which }) {
  const [src, setSrc] = useState(null)
  const [kind, setKind] = useState('')
  const [err, setErr] = useState('')

  useEffect(() => {
    let url
    let dead = false
    setSrc(null)
    setErr('')
    api.get(`/university/requests/${requestId}/document/${which}/`, { responseType: 'blob' })
      .then((r) => { if (dead) return; url = URL.createObjectURL(r.data); setKind(r.data.type); setSrc(url) })
      .catch(() => !dead && setErr('Could not load this document.'))
    return () => { dead = true; if (url) URL.revokeObjectURL(url) }
  }, [requestId, which])

  if (err) return <Alert>{err}</Alert>
  if (!src) return <p className="p-6 text-sm text-teal-soft">Loading document…</p>
  return kind.startsWith('image/')
    ? <img src={src} alt={which === 'degree' ? 'Degree certificate' : 'Mark sheet'} className="mx-auto max-h-[70vh] object-contain" />
    : <iframe src={src} title={which === 'degree' ? 'Degree certificate' : 'Mark sheet'} className="h-[70vh] w-full rounded border border-beige-line bg-white" />
}

function ReviewDialog({ req, canIssue, onClose, onDone }) {
  const [which, setWhich] = useState('degree')
  const [step, setStep] = useState('review') // review -> confirm -> done
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [result, setResult] = useState(null)

  useEffect(() => {
    const h = (e) => e.key === 'Escape' && !busy && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [busy, onClose])

  const act = async (kind) => {
    setBusy(true)
    setErr('')
    try {
      const r = await api.post(`/university/requests/${req.id}/${kind}/`)
      if (kind === 'sign') { setResult(r.data); setStep('done') } else { onDone(); onClose() }
    } catch (x) {
      setErr(errMsg(x))
      setStep('review')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-teal/60 p-3 sm:p-6" onMouseDown={(e) => e.target === e.currentTarget && !busy && onClose()}>
      <div role="dialog" aria-modal="true" aria-label={`Review ${req.course} for ${req.teacher_name}`} className="w-full max-w-4xl rounded-lg bg-beige p-5 shadow-xl">
        <div className="mb-3 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">{req.teacher_name}</h2>
            <p className="text-sm text-teal-soft">{req.course}{req.specialization && `, ${req.specialization}`} · {req.level_label} · {req.year_of_passing}{req.marks && ` · ${req.marks}`}</p>
          </div>
          <button onClick={onClose} disabled={busy} className="text-sm font-semibold underline">Close</button>
        </div>

        {step === 'done' ? (
          <div className="space-y-3 rounded-md border border-green-300 bg-green-50 p-4 text-sm text-green-900">
            <p className="text-base font-bold">Degree issued and signed ✓</p>
            <p>The teacher has been notified. Anyone can now verify this degree with your public key.</p>
            <dl className="space-y-1 font-mono text-xs">
              <div><dt className="inline font-sans font-semibold">SHA-256: </dt><dd className="inline break-all">{result.document_sha256}</dd></div>
              <div><dt className="inline font-sans font-semibold">Signature: </dt><dd className="inline break-all">{short(result.signature, 20)}</dd></div>
              <div><dt className="inline font-sans font-semibold">Signed at: </dt><dd className="inline">{when(result.signed_at)}</dd></div>
            </dl>
            <button className="btn" onClick={() => { onDone(); onClose() }}>Back to requests</button>
          </div>
        ) : (
          <>
            <div role="tablist" aria-label="Document" className="mb-3 flex gap-2">
              {[['degree', 'Degree certificate'], ['marksheet', 'Mark sheet']].map(([k, t]) => (
                <button key={k} role="tab" aria-selected={which === k} onClick={() => setWhich(k)}
                  className={`rounded-md border px-3 py-1.5 text-sm font-semibold ${which === k ? 'border-teal bg-teal text-beige' : 'border-beige-line'}`}>{t}</button>
              ))}
            </div>
            <div className="rounded-md bg-beige-dark/50 p-2"><DocumentViewer requestId={req.id} which={which} /></div>

            <div className="mt-4 space-y-3">
              <Alert>{err}</Alert>
              {step === 'review' && (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <button className="btn-danger" disabled={busy} onClick={() => window.confirm('Tell the teacher you cannot verify this degree?') && act('reject')}>Cannot verify</button>
                  <button className="btn" disabled={!canIssue || busy} onClick={() => setStep('confirm')}>Issue &amp; Sign</button>
                </div>
              )}
              {step === 'confirm' && (
                <div role="alertdialog" aria-label="Confirm signing" className="rounded-md border border-teal bg-white p-4 text-sm">
                  <p className="font-bold">Sign this degree with your university's private key?</p>
                  <p className="mt-1 text-teal-soft">
                    You attest that <strong>{req.teacher_name}</strong> was awarded <strong>{req.course}</strong> ({req.year_of_passing}) by your university,
                    and that the certificate you just viewed is genuine. Aeterna fingerprints that exact file (SHA-256) and signs it together with these details. It cannot be undone.
                  </p>
                  <div className="mt-3 flex gap-3">
                    <button className="btn" disabled={busy} onClick={() => act('sign')}>{busy ? 'Signing…' : 'Yes, issue and sign'}</button>
                    <button className="btn-outline" disabled={busy} onClick={() => setStep('review')}>Go back</button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

const TABS = [['pending', 'Pending requests'], ['signed', 'Issued'], ['rejected', 'Not verified']]

export default function UniversityDashboard() {
  const [profile, setProfile] = useState(null)
  const [tab, setTab] = useState('pending')
  const [rows, setRows] = useState(null)
  const [pendingCount, setPendingCount] = useState(null)
  const [review, setReview] = useState(null)
  const [err, setErr] = useState('')

  const loadProfile = useCallback(() => api.get('/university/profile/').then((r) => setProfile(r.data)).catch((x) => setErr(errMsg(x))), [])
  const load = useCallback(() => {
    setRows(null)
    api.get('/university/requests/', { params: { status: tab } }).then((r) => setRows(r.data)).catch((x) => setErr(errMsg(x)))
    api.get('/university/requests/', { params: { status: 'pending' } }).then((r) => setPendingCount(r.data.length)).catch(() => {})
  }, [tab])
  useEffect(() => { loadProfile() }, [loadProfile])
  useEffect(() => { load() }, [load])

  if (!profile) return err ? <Alert>{err}</Alert> : <p>Loading…</p>
  const canIssue = profile.can_issue

  return (
    <div className="space-y-6">
      <section className="card flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">{profile.name}</h1>
          <p className="mt-1 text-sm text-teal-soft">
            {[profile.city, profile.state].filter(Boolean).join(', ')}{profile.nirf_rank ? ` · NIRF rank #${profile.nirf_rank}` : ' · NIRF rank not set'}
          </p>
        </div>
        <div className="text-right text-sm">
          <Chip className={canIssue ? 'bg-green-100 text-green-900' : 'bg-yellow-100 text-yellow-900'}>{canIssue ? 'Verified issuer' : profile.verification_status === 'rejected' ? 'Not approved' : 'Awaiting Aeterna verification'}</Chip>
          {profile.key_fingerprint && <p className="mt-2 text-xs text-teal-soft">Signing key <span className="font-mono">{profile.key_fingerprint}</span></p>}
        </div>
      </section>

      {!canIssue && (
        <Alert>
          {profile.verification_status === 'verified'
            ? 'Your signing rights are suspended. Contact Aeterna support.'
            : 'Aeterna is verifying your university. Once approved, your signing key is created and you can issue degrees. Teachers cannot select your university until then.'}
        </Alert>
      )}

      <section className="card">
        <div role="tablist" aria-label="Degree requests" className="mb-4 flex flex-wrap gap-2">
          {TABS.map(([k, t]) => (
            <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
              className={`rounded-md border px-3 py-1.5 text-sm font-semibold ${tab === k ? 'border-teal bg-teal text-beige' : 'border-beige-line'}`}>
              {t}{k === 'pending' && pendingCount > 0 && <span className="ml-2 rounded-full bg-red-600 px-1.5 text-xs text-white">{pendingCount}</span>}
            </button>
          ))}
        </div>

        <Alert>{err}</Alert>
        {rows === null && <p className="text-sm text-teal-soft">Loading…</p>}
        {rows?.length === 0 && (
          <p className="text-sm text-teal-soft">
            {tab === 'pending' ? 'No pending requests. When a teacher picks your university for a degree, it appears here.' : 'Nothing here yet.'}
          </p>
        )}
        <ul className="divide-y divide-beige-line">
          {rows?.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="text-sm">
                <p className="font-semibold">{r.teacher_name}</p>
                <p className="text-teal-soft">{r.course}{r.specialization && `, ${r.specialization}`} · {r.level_label} · {r.year_of_passing}{r.marks && ` · ${r.marks}`}</p>
                {tab === 'pending' && <p className="text-xs text-teal-soft">Requested {when(r.created_at)}</p>}
                {tab === 'signed' && <p className="text-xs text-teal-soft">Signed {when(r.signed_at)} · <span className="font-mono">{short(r.document_sha256, 8)}</span></p>}
              </div>
              {tab === 'pending' && <button className="btn" onClick={() => setReview(r)}>Review &amp; sign</button>}
              {tab === 'signed' && <VerificationBadge q={r} />}
              {tab === 'rejected' && <Chip className="bg-red-100 text-red-900">Not verified</Chip>}
            </li>
          ))}
        </ul>
      </section>

      {review && <ReviewDialog req={review} canIssue={canIssue} onClose={() => setReview(null)} onDone={load} />}
    </div>
  )
}
