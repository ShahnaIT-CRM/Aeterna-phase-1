import { useEffect, useState } from 'react'
import api, { errMsg } from '../api'
import { Alert } from '../components/ui'
import { BlockchainBadge } from '../components/BlockchainBadge'

function Row({ q, onIssued }) {
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const issue = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    const fd = new FormData()
    fd.append('document', file)
    try {
      onIssued((await api.post(`/institute/credentials/${q.id}/issue/`, fd)).data)
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="py-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold">{q.teacher_name} · {q.course}{q.specialization && `, ${q.specialization}`}</p>
          <p className="text-teal-soft">{q.university} · {q.year_of_passing}{q.marks && ` · ${q.marks}`}</p>
        </div>
        {q.blockchain_verified ? (
          <BlockchainBadge q={q} />
        ) : (
          <form onSubmit={issue} className="flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor={`doc${q.id}`}>Official certificate for {q.teacher_name}</label>
            <input id={`doc${q.id}`} type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(e) => setFile(e.target.files[0])} />
            <button className="btn" disabled={!file || busy}>{busy ? 'Anchoring…' : 'Anchor on blockchain'}</button>
          </form>
        )}
      </div>
      <Alert>{err}</Alert>
    </li>
  )
}

export default function IssueCredentials() {
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => { api.get('/institute/credentials/').then((r) => setRows(r.data)).catch((x) => setErr(errMsg(x))) }, [])
  const replace = (q) => setRows((rs) => rs.map((r) => (r.id === q.id ? q : r)))

  return (
    <section className="card space-y-3">
      <div>
        <h2 className="text-xl font-bold">Issue verified credentials</h2>
        <p className="text-sm text-teal-soft">
          Teachers who list your institute as their university appear here. Upload your official certificate and we
          record its fingerprint on the blockchain, so hiring institutes can confirm it in seconds.
          Your institute must be verified by Aeterna first.
        </p>
      </div>
      <Alert>{err}</Alert>
      {rows === null && !err && <p>Loading…</p>}
      {rows?.length === 0 && <p className="text-sm">No degrees name your institute yet. Matching uses your registered institute name.</p>}
      <ul className="divide-y divide-beige-line">{rows?.map((q) => <Row key={q.id} q={q} onIssued={replace} />)}</ul>
    </section>
  )
}
