import { useEffect, useState } from 'react'
import api, { errMsg } from '../api'
import { Alert } from '../components/ui'
import { APP_STATUS, JOB_STATUS, label } from '../constants'

// Pipeline order, with the three headline statuses first.
const FEATURED = ['applied', 'shortlisted', 'hired']
const OTHER = ['viewed', 'interview', 'offered', 'rejected', 'bookmarked']
const BAR = { applied: 'bg-teal-soft', shortlisted: 'bg-teal-light', hired: 'bg-teal' }

function Stat({ title, value, hint }) {
  return (
    <div className="card">
      <p className="text-sm font-semibold text-teal-soft">{title}</p>
      <p className="font-display text-4xl font-bold">{value}</p>
      {hint && <p className="mt-1 text-xs text-teal-soft">{hint}</p>}
    </div>
  )
}

export default function InstituteAnalytics() {
  const [d, setD] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => { api.get('/institute/analytics/').then((r) => setD(r.data)).catch((x) => setErr(errMsg(x))) }, [])

  if (err) return <Alert>{err}</Alert>
  if (!d) return <p>Loading…</p>

  const by = d.applications_by_status
  const max = Math.max(1, ...Object.values(by))
  const row = (k) => (
    <li key={k} className="grid grid-cols-[9rem_1fr_2.5rem] items-center gap-3 text-sm">
      <span className={FEATURED.includes(k) ? 'font-semibold' : ''}>{label(APP_STATUS, k)}</span>
      <div className="h-3 overflow-hidden rounded-full bg-beige-dark" role="img" aria-label={`${label(APP_STATUS, k)}: ${by[k]}`}>
        <div className={`h-full ${BAR[k] || 'bg-teal-soft/60'}`} style={{ width: `${(by[k] / max) * 100}%` }} />
      </div>
      <span className="text-right font-semibold">{by[k]}</span>
    </li>
  )

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <Stat title="Active jobs" value={d.active_jobs} hint={`${d.total_jobs} posted in total. Active means open and before the deadline.`} />
        <Stat title="Applications received" value={d.total_applications} />
      </div>

      <section className="card">
        <h2 className="text-xl font-bold">Applicants by status</h2>
        <p className="mb-4 text-sm text-teal-soft">“Applied” counts candidates you haven’t opened yet.</p>
        <ul className="space-y-3">
          {FEATURED.map(row)}
          <li className="border-t border-beige-line" aria-hidden="true" />
          {OTHER.map(row)}
        </ul>
      </section>

      <section className="card">
        <h2 className="mb-3 text-xl font-bold">By job</h2>
        {d.per_job.length === 0 ? <p className="text-sm text-teal-soft">No jobs posted yet.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-beige-line"><th className="py-2 pr-4">Job</th><th className="pr-4">Status</th><th className="pr-4 text-right">Applications</th><th className="pr-4 text-right">Shortlisted</th><th className="text-right">Hired</th></tr></thead>
              <tbody>
                {d.per_job.map((j) => (
                  <tr key={j.job_id} className="border-b border-beige-line/60">
                    <td className="py-2 pr-4 font-semibold">{j.title}</td>
                    <td className="pr-4">{label(JOB_STATUS, j.status)}</td>
                    <td className="pr-4 text-right">{j.applications}</td>
                    <td className="pr-4 text-right">{j.shortlisted}</td>
                    <td className="text-right">{j.hired}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
