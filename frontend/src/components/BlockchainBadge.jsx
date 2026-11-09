import { useState } from 'react'
import api, { errMsg } from '../api'
import { VerifyChip } from './ui'

const short = (h) => `${h.slice(0, 10)}…${h.slice(-6)}`

/** "Blockchain Verified" badge. Click it to re-check the anchored document against the chain. */
export function BlockchainBadge({ q }) {
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const check = async () => {
    if (res || busy) return setRes(null)
    setBusy(true)
    setErr('')
    try {
      setRes((await api.get(`/credentials/verify/${q.blockchain_tx_hash}/`)).data)
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(false)
    }
  }

  return (
    <span className="inline-block align-middle">
      <button
        type="button"
        onClick={check}
        aria-expanded={!!res}
        title={`Transaction ${q.blockchain_tx_hash}. Click to check.`}
        className="inline-flex items-center gap-1 rounded-full bg-teal px-2.5 py-0.5 text-xs font-semibold text-beige hover:bg-teal-light"
      >
        <span aria-hidden="true">✓</span> Blockchain Verified
      </button>
      {busy && <span className="ml-2 text-xs">Checking…</span>}
      {err && <span className="ml-2 text-xs text-red-800">{err}</span>}
      {res && (
        <span role="status" className={`mt-1 block text-xs ${res.valid ? 'text-teal-soft' : 'font-semibold text-red-800'}`}>
          {res.valid
            ? <>Document intact · issued by {res.issued_by} · block {res.block_number} · tx {short(res.tx_hash)}</>
            : 'Warning: the stored document no longer matches what was anchored.'}
        </span>
      )}
    </span>
  )
}

/** Use wherever a degree is listed: the blockchain badge when anchored, else the normal status chip. */
export function QualificationBadge({ q }) {
  return q.blockchain_verified ? <BlockchainBadge q={q} /> : <VerifyChip status={q.verification_status} />
}
