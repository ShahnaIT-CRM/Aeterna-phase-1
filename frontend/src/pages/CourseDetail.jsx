import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { errMsg } from '../api'
import { Alert, Chip } from '../components/ui'
import { LEVEL_LABEL, ProgressBar } from './Courses'

export default function CourseDetail() {
  const { id } = useParams()
  const [course, setCourse] = useState(null)
  const [err, setErr] = useState('')
  const [open, setOpen] = useState(null)
  const [busy, setBusy] = useState(null)

  const load = () => api.get(`/lms/courses/${id}/`).then((r) => setCourse(r.data)).catch((x) => setErr(errMsg(x)))
  useEffect(() => { load() }, [id])

  const enroll = async () => {
    setErr('')
    try {
      await api.post(`/lms/courses/${id}/enroll/`)
      await load()
    } catch (x) {
      setErr(errMsg(x))
    }
  }

  const complete = async (lesson) => {
    setBusy(lesson.id)
    setErr('')
    try {
      await api.post(`/lms/enrollments/${course.enrollment_id}/complete-lesson/`, { lesson: lesson.id })
      await load()
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(null)
    }
  }

  if (!course) return err ? <Alert>{err}</Alert> : <p>Loading…</p>
  const enrolled = course.enrollment_id != null

  return (
    <div className="space-y-5">
      <Link to="/courses" className="text-sm font-semibold underline">← All courses</Link>
      <div>
        <div className="mb-2 flex gap-2"><Chip>{LEVEL_LABEL[course.level] || course.level}</Chip></div>
        <h1 className="text-3xl font-bold">{course.title}</h1>
        <p className="mt-1">{course.description || course.summary}</p>
        <p className="mt-1 text-xs text-teal-soft">{course.lesson_count} lessons · {course.total_minutes} min · Badge: {course.badge}</p>
      </div>
      <Alert>{err}</Alert>

      {!enrolled && <div><button className="btn" onClick={enroll}>Enroll to start learning</button></div>}
      {enrolled && (
        <div className="space-y-2">
          <ProgressBar value={course.progress} />
          <p className="text-sm">{course.progress}% complete</p>
          {course.enrollment_status === 'completed' && (
            <Alert kind="ok">You completed this course and earned the “{course.badge}” badge.</Alert>
          )}
        </div>
      )}

      <ol className="space-y-3">
        {course.lessons.map((l) => (
          <li key={l.id} className="card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-bold">{l.order}. {l.title} {l.completed && <Chip className="ml-1 bg-green-100 text-green-900">Done</Chip>}</p>
                <p className="text-xs text-teal-soft">{l.duration_minutes} min</p>
              </div>
              {enrolled && (
                <button className="text-sm font-semibold underline" aria-expanded={open === l.id} onClick={() => setOpen(open === l.id ? null : l.id)}>
                  {open === l.id ? 'Hide lesson' : 'Open lesson'}
                </button>
              )}
            </div>
            {enrolled && open === l.id && (
              <div className="mt-3 space-y-3 border-t border-beige-line pt-3 text-sm">
                {l.content && <p className="whitespace-pre-line">{l.content}</p>}
                {l.video_url && <p><a className="underline" href={l.video_url} target="_blank" rel="noreferrer">Watch the lesson video</a></p>}
                {!l.completed && <button className="btn" disabled={busy === l.id} onClick={() => complete(l)}>{busy === l.id ? 'Saving…' : 'Mark as complete'}</button>}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  )
}
