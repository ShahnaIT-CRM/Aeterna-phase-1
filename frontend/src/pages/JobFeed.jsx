import { useEffect, useState } from 'react'
import api, { errMsg } from '../api'
import { Alert, Chip, Modal } from '../components/ui'
import { EMPLOYMENT_TYPES, WORK_MODES, label, money } from '../constants'

export function salaryText(j) {
  if (j.salary_display === 'industry') return 'As per industry standards'
  if (j.salary_min == null && j.salary_max == null) return ''
  return `${money(j.salary_min)} to ${money(j.salary_max)} per year${j.salary_negotiable ? ' (negotiable)' : ''}`
}

function ApplyModal({ job, onClose, onApplied }) {
  const [cover, setCover] = useState('')
  const [answers, setAnswers] = useState({})
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [docs, setDocs] = useState(null) // what will be auto-attached

  useEffect(() => {
    Promise.all([api.get('/teacher/qualifications/'), api.get('/teacher/certifications/')])
      .then(([q, c]) => setDocs({
        degrees: q.data.filter((x) => x.degree_certificate || x.marksheet).length,
        certs: c.data.filter((x) => x.document).length,
      }))
      .catch(() => setDocs(null))
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const { data } = await api.post(`/jobs/${job.id}/apply/`, {
        cover_letter: cover,
        answers: job.questions.map((q) => ({ question: q.id, answer: answers[q.id] || '' })),
      })
      onApplied(job.id, data.match_score)
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={`Apply: ${job.title}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-teal-soft">Your profile, qualifications and certifications are shared with {job.institute_name} when you apply.</p>
        {docs && (
          <p className="rounded-md bg-beige-dark/60 px-3 py-2 text-sm">
            {docs.degrees + docs.certs > 0
              ? `We’ll attach your uploaded documents automatically: ${docs.degrees} degree or mark sheet file${docs.degrees === 1 ? '' : 's'} and ${docs.certs} certificate${docs.certs === 1 ? '' : 's'}.`
              : 'You haven’t uploaded any degree or certificate files yet. Add them under My profile and they’ll be attached to future applications automatically.'}
          </p>
        )}
        <div>
          <label className="label" htmlFor="cl">Cover letter (optional)</label>
          <textarea id="cl" rows={5} className="input" value={cover} onChange={(e) => setCover(e.target.value)} />
        </div>
        {job.questions.map((q) => (
          <div key={q.id}>
            <label className="label" htmlFor={`q${q.id}`}>{q.text}</label>
            <textarea id={`q${q.id}`} rows={3} required className="input" value={answers[q.id] || ''} onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })} />
          </div>
        ))}
        <Alert>{err}</Alert>
        <button className="btn" disabled={busy}>{busy ? 'Sending…' : 'Submit application'}</button>
      </form>
    </Modal>
  )
}

export default function JobFeed() {
  const [filters, setFilters] = useState({ q: '', employment_type: '', work_mode: '', city: '', max_experience: '' })
  const [jobs, setJobs] = useState([])
  const [next, setNext] = useState(1)
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [applying, setApplying] = useState(null)
  const [flash, setFlash] = useState('')

  const fetchPage = async (page, replace) => {
    setLoading(true)
    setErr('')
    try {
      const params = Object.fromEntries(Object.entries({ ...filters, page }).filter(([, v]) => v !== ''))
      const { data } = await api.get('/jobs/', { params })
      setJobs((j) => (replace ? data.results : [...j, ...data.results]))
      setCount(data.count)
      setNext(data.next ? page + 1 : null)
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { fetchPage(1, true) }, [])

  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value })
  const search = (e) => { e.preventDefault(); fetchPage(1, true) }
  const applied = (id, score) => {
    setJobs((js) => js.map((j) => (j.id === id ? { ...j, has_applied: true } : j)))
    setApplying(null)
    setFlash(`Application sent${score != null ? ` (${Math.round(score)}% match)` : ''}. Track its status under My applications.`)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Find your next teaching role</h1>

      <form onSubmit={search} className="card grid gap-3 md:grid-cols-6">
        <div className="md:col-span-2"><label className="label" htmlFor="fq">Role, subject or institute</label><input id="fq" className="input" value={filters.q} onChange={set('q')} placeholder="PGT Physics" /></div>
        <div><label className="label" htmlFor="fc">City</label><input id="fc" className="input" value={filters.city} onChange={set('city')} /></div>
        <div>
          <label className="label" htmlFor="fe">Job type</label>
          <select id="fe" className="input" value={filters.employment_type} onChange={set('employment_type')}><option value="">Any</option>{EMPLOYMENT_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        </div>
        <div>
          <label className="label" htmlFor="fw">Work mode</label>
          <select id="fw" className="input" value={filters.work_mode} onChange={set('work_mode')}><option value="">Any</option>{WORK_MODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        </div>
        <div><label className="label" htmlFor="fx">My experience (years)</label><input id="fx" type="number" min="0" className="input" value={filters.max_experience} onChange={set('max_experience')} /></div>
        <div className="md:col-span-6"><button className="btn">Search jobs</button></div>
      </form>

      <Alert kind="ok">{flash}</Alert>
      <Alert>{err}</Alert>
      {!loading && jobs.length === 0 && !err && <p>No open jobs match your search. Try removing a filter.</p>}
      {jobs.length > 0 && <p className="text-sm text-teal-soft">{count} open {count === 1 ? 'job' : 'jobs'}</p>}

      <div className="grid gap-4 md:grid-cols-2">
        {jobs.map((j) => (
          <article key={j.id} className="card flex flex-col">
            <h2 className="text-xl font-bold">{j.title}</h2>
            <p className="text-sm">
              {j.institute_name}{j.institute_verified && <Chip className="ml-2 bg-green-100 text-green-900">Verified institute</Chip>}
            </p>
            <p className="text-sm text-teal-soft">{[j.city, j.state].filter(Boolean).join(', ')}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Chip>{label(EMPLOYMENT_TYPES, j.employment_type)}</Chip>
              <Chip>{label(WORK_MODES, j.work_mode)}</Chip>
              {j.designation && <Chip>{j.designation}</Chip>}
              {j.curriculum && <Chip>{j.curriculum}</Chip>}
              {j.min_experience_years > 0 && <Chip>{j.min_experience_years}+ years</Chip>}
            </div>
            <p className="mt-3 line-clamp-3 flex-1 text-sm">{j.description}</p>
            {j.mandatory_certifications?.length > 0 && <p className="mt-2 text-sm"><b>Required:</b> {j.mandatory_certifications.join(', ')}</p>}
            {salaryText(j) && <p className="mt-2 text-sm font-semibold">{salaryText(j)}</p>}
            <div className="mt-4 flex items-center justify-between">
              <span className="text-xs text-teal-soft">{j.application_deadline ? `Apply by ${j.application_deadline}` : ''}</span>
              {j.has_applied ? <Chip className="bg-green-100 text-green-900">Applied</Chip> : <button className="btn" onClick={() => { setFlash(''); setApplying(j) }}>Apply</button>}
            </div>
          </article>
        ))}
      </div>

      {next && <button className="btn-outline" disabled={loading} onClick={() => fetchPage(next, false)}>{loading ? 'Loading…' : 'Show more jobs'}</button>}
      {applying && <ApplyModal job={applying} onClose={() => setApplying(null)} onApplied={applied} />}
    </div>
  )
}
