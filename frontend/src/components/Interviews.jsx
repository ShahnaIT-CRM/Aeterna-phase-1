import { useEffect, useState } from 'react'
import api, { errMsg } from '../api'
import { fmtDateTime } from '../constants'
import { Alert, Modal } from './ui'

// Value for <input type="datetime-local" min=...>: the current local time, to the minute.
const localNow = () => {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

/** Institute: pick a date/time and say where. Calling it again on a scheduled application reschedules. */
export function ScheduleInterviewModal({ app, onClose, onScheduled }) {
  const [when, setWhen] = useState(app.interview_date ? toLocalInput(app.interview_date) : '')
  const [details, setDetails] = useState(app.interview_details || '')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const r = await api.post(`/applications/${app.id}/schedule-interview/`, {
        interview_date: new Date(when).toISOString(), // the browser's local time, sent with its UTC offset
        interview_details: details,
      })
      onScheduled(r.data)
      onClose()
    } catch (x) {
      setErr(errMsg(x))
      setBusy(false)
    }
  }

  return (
    <Modal title={`${app.interview_date ? 'Reschedule' : 'Schedule'} interview: ${app.teacher_name}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label" htmlFor="iv-when">Date and time</label>
          <input id="iv-when" type="datetime-local" className="input" required min={localNow()} value={when} onChange={(e) => setWhen(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="iv-where">Where or how (meeting link, room, address)</label>
          <input id="iv-where" className="input" maxLength={300} value={details} onChange={(e) => setDetails(e.target.value)} placeholder="e.g. https://meet.google.com/abc-defg-hij" />
        </div>
        <p className="text-xs text-teal-soft">The candidate is emailed the details and sees it under My applications.</p>
        <Alert>{err}</Alert>
        <div className="flex gap-3">
          <button className="btn" disabled={busy || !when}>{busy ? 'Saving…' : 'Send invitation'}</button>
          <button type="button" className="btn-outline" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </Modal>
  )
}

function toLocalInput(iso) {
  const d = new Date(iso)
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

/** Teacher: upcoming interviews, soonest first. */
export function UpcomingInterviews() {
  const [items, setItems] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => { api.get('/applications/interviews/').then((r) => setItems(r.data)).catch((x) => setErr(errMsg(x))) }, [])

  return (
    <section className="card space-y-3" aria-labelledby="upcoming-h">
      <h2 id="upcoming-h" className="text-xl font-bold">Upcoming interviews</h2>
      <Alert>{err}</Alert>
      {items === null && !err && <p className="text-sm">Loading…</p>}
      {items?.length === 0 && <p className="text-sm text-teal-soft">No interviews scheduled yet. When an institute invites you, it shows up here.</p>}
      <ul className="divide-y divide-beige-line">
        {items?.map((a) => (
          <li key={a.id} className="py-3 text-sm">
            <p className="font-bold">{fmtDateTime(a.interview_date)}</p>
            <p>{a.job_title} · {a.institute_name}{a.job_city && ` · ${a.job_city}`}</p>
            {a.interview_details && <p className="text-teal-soft">{a.interview_details}</p>}
          </li>
        ))}
      </ul>
    </section>
  )
}
