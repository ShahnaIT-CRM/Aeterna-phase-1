import { useState } from 'react'
import api, { errMsg, publicApi } from '../api'
import { VerifyChip } from './ui'

const short = (h = '', a = 8, b = 6) => (h.length > a + b + 1 ? `${h.slice(0, a)}…${h.slice(-b)}` : h)
const when = (d) => (d ? new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '')

const PROBLEM = {
  signature_invalid: 'The signature does not match this degree record. Treat it as unverified.',
  document_altered: 'The stored certificate was changed after the university signed it.',
  issuer_revoked: 'The issuing university no longer holds signing rights.',
  unsigned: 'The university has not signed this degree.',
  not_found: 'No record found.',
}

function Tick({ className = 'h-5 w-5' }) {
  return (
    <svg viewBox="0 0 20 20" className={className} aria-hidden="true">
      <circle cx="10" cy="10" r="10" fill="#16a34a" />
      <path d="M5.5 10.4l3 3 6-6.4" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

/**
 * "Cryptographically Verified" badge with a green check. Clicking it asks the server to re-check the
 * Ed25519 signature and the stored file's SHA-256 right now, and shows the evidence.
 *   q          a qualification (needs q.id)
 *   anonymous  true on public pages: sends no login token
 *   tone       'light' (default) or 'glass' for dark glass cards
 */
export default function VerificationBadge({ q, anonymous = false, tone = 'light' }) {
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [open, setOpen] = useState(false)

  const check = async () => {
    setOpen((o) => !o)
    if (res || busy) return
    setBusy(true)
    setErr('')
    try {
      setRes((await (anonymous ? publicApi : api).get(`/credentials/verify/${q.id}/`)).data)
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(false)
    }
  }

  const glass = tone === 'glass'
  const ok = !res || res.valid
  return (
    <div className="inline-block max-w-full text-left align-top">
      <button
        type="button" onClick={check} aria-expanded={open}
        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold transition ${
          ok
            ? glass ? 'border-emerald-300/50 bg-emerald-400/15 text-emerald-100 hover:bg-emerald-400/25' : 'border-green-300 bg-green-50 text-green-900 hover:bg-green-100'
            : 'border-red-300 bg-red-50 text-red-900'
        }`}
      >
        {ok ? <Tick className="h-4 w-4" /> : <span aria-hidden="true">⚠</span>}
        {ok ? 'Cryptographically Verified' : 'Verification failed'}
      </button>

      {open && (
        <div className={`mt-2 w-72 max-w-full rounded-md border p-3 text-xs leading-relaxed ${glass ? 'border-white/20 bg-black/40 text-white backdrop-blur' : 'border-beige-line bg-white text-teal'}`} role="status">
          {busy && <p>Checking the signature…</p>}
          {err && <p className="text-red-700">{err}</p>}
          {res && !res.valid && <p className="font-semibold text-red-700">{PROBLEM[res.status] || res.detail}</p>}
          {res && res.issued_by && (
            <dl className="space-y-1">
              <div><dt className="inline font-semibold">Issued by: </dt><dd className="inline">{res.issued_by}{res.issuer_nirf_rank ? ` (NIRF #${res.issuer_nirf_rank})` : ''}</dd></div>
              <div><dt className="inline font-semibold">Signed: </dt><dd className="inline">{when(res.signed_at)}</dd></div>
              <div><dt className="inline font-semibold">Signature: </dt><dd className="inline">{res.signature_valid ? '✓ valid' : '✗ invalid'} ({res.algorithm})</dd></div>
              <div><dt className="inline font-semibold">Document: </dt><dd className="inline">{res.document_intact ? '✓ unaltered' : '✗ changed since signing'}</dd></div>
              <div><dt className="inline font-semibold">SHA-256: </dt><dd className="inline break-all font-mono" title={res.document_sha256}>{short(res.document_sha256)}</dd></div>
              <div><dt className="inline font-semibold">Issuer key: </dt><dd className="inline font-mono">{res.key_fingerprint}</dd></div>
            </dl>
          )}
          {res?.valid && <p className="mt-2 opacity-70">Checked just now against the university's public key.</p>}
        </div>
      )}
    </div>
  )
}

/** Wherever a degree is listed: the green badge when the university signed it, else the plain status chip. */
export function QualificationBadge({ q, anonymous, tone }) {
  return q.cryptographically_verified
    ? <VerificationBadge q={q} anonymous={anonymous} tone={tone} />
    : <VerifyChip status={q.verification_status} />
}
