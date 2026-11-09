import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api, { errMsg } from '../api'
import { Alert, Chip } from '../components/ui'

export const LEVEL_LABEL = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' }

export function ProgressBar({ value }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-beige-dark" role="img" aria-label={`${value}% complete`}>
      <div className="h-full bg-teal-light" style={{ width: `${value}%` }} />
    </div>
  )
}

export default function Courses() {
  const [courses, setCourses] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(null)
  const nav = useNavigate()

  useEffect(() => { api.get('/lms/courses/').then((r) => setCourses(r.data)).catch((x) => setErr(errMsg(x))) }, [])

  const enroll = async (c) => {
    setBusy(c.id)
    setErr('')
    try {
      await api.post(`/lms/courses/${c.id}/enroll/`)
      nav(`/courses/${c.id}`)
    } catch (x) {
      setErr(errMsg(x))
      setBusy(null)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-bold">Micro-courses</h1>
        <p className="text-sm text-teal-soft">Short skill boosters. Finish a course to earn a digital badge.</p>
      </div>
      <Alert>{err}</Alert>
      {courses === null && !err && <p>Loading…</p>}
      {courses?.length === 0 && <p>No courses are published yet. Check back soon.</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {courses?.map((c) => {
          const enrolled = c.enrollment_id != null
          return (
            <article key={c.id} className="card flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Chip>{LEVEL_LABEL[c.level] || c.level}</Chip>
                {c.enrollment_status === 'completed' && <Chip className="bg-green-100 text-green-900">Completed</Chip>}
              </div>
              <div>
                <h2 className="text-lg font-bold">{c.title}</h2>
                <p className="text-sm">{c.summary}</p>
              </div>
              <p className="text-xs text-teal-soft">
                {c.lesson_count} lesson{c.lesson_count === 1 ? '' : 's'} · {c.total_minutes} min · Badge: {c.badge}
              </p>
              {enrolled && <ProgressBar value={c.progress} />}
              <div className="mt-auto">
                {enrolled ? (
                  <Link className="btn-outline" to={`/courses/${c.id}`}>{c.enrollment_status === 'completed' ? 'Review course' : 'Continue'}</Link>
                ) : (
                  <button className="btn" disabled={busy === c.id || c.lesson_count === 0} onClick={() => enroll(c)}>
                    {busy === c.id ? 'Enrolling…' : c.lesson_count === 0 ? 'Coming soon' : 'Enroll'}
                  </button>
                )}
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
