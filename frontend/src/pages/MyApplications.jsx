import { useEffect, useState } from 'react'
import api, { errMsg } from '../api'
import { Alert, Chip } from '../components/ui'
import { MatchBadge } from '../components/Match'
import { UpcomingInterviews } from '../components/Interviews'
import { APP_STATUS, fmtDateTime, label } from '../constants'

const STYLE = {
  applied: '', viewed: 'bg-blue-100 text-blue-900', shortlisted: 'bg-green-100 text-green-900',
  interview: 'bg-green-100 text-green-900', offered: 'bg-green-200 text-green-900', hired: 'bg-green-300 text-green-950',
  rejected: 'bg-red-100 text-red-900', bookmarked: 'bg-orange-100 text-orange-900',
}

export default function MyApplications() {
  const [apps, setApps] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => { api.get('/applications/').then((r) => setApps(r.data)).catch((x) => setErr(errMsg(x))) }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold">My applications</h1>
      <UpcomingInterviews />
      <Alert>{err}</Alert>
      {apps === null && !err && <p>Loading…</p>}
      {apps?.length === 0 && <p>You haven’t applied to any jobs yet. Browse open roles under Find jobs.</p>}
      {apps?.map((a) => (
        <article key={a.id} className="card flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold">{a.job_title}</h2>
            <p className="text-sm text-teal-soft">{a.institute_name}{a.job_city && ` · ${a.job_city}`} · applied {new Date(a.applied_at).toLocaleDateString('en-IN')}</p>
            {a.status === 'interview' && (
              <p className="mt-1 text-sm font-semibold">{a.interview_date ? `Interview: ${fmtDateTime(a.interview_date)}` : 'Interview: date to be confirmed'}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <MatchBadge score={a.match_score} />
            <Chip className={STYLE[a.status]}>{label(APP_STATUS, a.status)}</Chip>
          </div>
        </article>
      ))}
    </div>
  )
}
