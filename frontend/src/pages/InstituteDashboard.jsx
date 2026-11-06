import { useEffect, useState } from 'react'
import api, { errMsg } from '../api'
import { Alert, Chip, FileUpload, FormFields, VerifyChip, buildPayload } from '../components/ui'
import {
  APP_STATUS, BOARDS, DESIGNATIONS, EMPLOYMENT_TYPES, INSTITUTE_TYPES, JOB_STATUS, SALARY_DISPLAY,
  WORK_MODES, label, money,
} from '../constants'
import { salaryText } from './JobFeed'
import InstituteAnalytics from './InstituteAnalytics'
import { AttachedDocuments, MatchBadge, MatchBreakdown } from '../components/Match'

const JOB_FIELDS = [
  { name: 'title', label: 'Job title', required: true, full: true, placeholder: 'PGT Physics' },
  { name: 'description', label: 'Job description', type: 'textarea', required: true, full: true, rows: 6, hint: 'Roles, responsibilities and expectations in as much detail as you can.' },
  { name: 'employment_type', label: 'Employment type', type: 'select', options: EMPLOYMENT_TYPES },
  { name: 'work_mode', label: 'Work mode', type: 'select', options: WORK_MODES },
  { name: 'designation', label: 'Designation', datalist: DESIGNATIONS },
  { name: 'department', label: 'Department', placeholder: 'Science, Commerce…' },
  { name: 'grade_level', label: 'Grade or level taught', placeholder: 'Grades 6-8' },
  { name: 'curriculum', label: 'Curriculum', datalist: BOARDS },
  { name: 'specialization', label: 'Specialization required', placeholder: 'Physics' },
  { name: 'min_experience_years', label: 'Minimum experience (years)', type: 'number', min: 0 },
  { name: 'mandatory_qualification', label: 'Mandatory qualification', placeholder: 'M.Sc. + B.Ed.' },
  { name: 'preferred_qualification', label: 'Preferred qualification', placeholder: 'Ph.D.' },
  { name: 'mandatory_certifications', label: 'Mandatory certifications', type: 'tags', placeholder: 'CTET, NET…' },
  { name: 'preferred_certifications', label: 'Preferred certifications', type: 'tags' },
  { name: 'skills', label: 'Key skills', type: 'tags', full: true, placeholder: 'Smart Board teaching, IB curriculum, student counselling…' },
  { name: 'salary_display', label: 'Salary display', type: 'select', options: SALARY_DISPLAY },
  { name: 'salary_negotiable', label: 'Salary is negotiable', type: 'checkbox' },
  { name: 'salary_min', label: 'Minimum salary (₹ per year)', type: 'number', nullable: true, min: 0 },
  { name: 'salary_max', label: 'Maximum salary (₹ per year)', type: 'number', nullable: true, min: 0 },
  { name: 'key_benefits', label: 'Key benefits', type: 'tags', full: true, placeholder: 'Health insurance, PF, accommodation…' },
  { name: 'other_benefits', label: 'Other monetary benefits', type: 'textarea', rows: 2, full: true, placeholder: 'Performance bonus up to ₹25,000, travel allowance ₹5,000 per month' },
  { name: 'city', label: 'City', required: true },
  { name: 'state', label: 'State' },
  { name: 'vacancies', label: 'Number of vacancies', type: 'number', min: 1 },
  { name: 'application_deadline', label: 'Application deadline', type: 'date', nullable: true },
  { name: 'joining_date', label: 'Tentative joining date', type: 'date', nullable: true },
  { name: 'status', label: 'Status', type: 'select', options: JOB_STATUS },
  { name: 'selection_process', label: 'Selection process', type: 'textarea', rows: 2, full: true, placeholder: 'Written test, demo lecture, two interview rounds' },
]

const INSTITUTE_FIELDS = [
  { name: 'name', label: 'Official registered name', required: true, full: true },
  { name: 'institute_type', label: 'Type of institute', type: 'select', options: INSTITUTE_TYPES },
  { name: 'year_established', label: 'Year of establishment', type: 'number', nullable: true, min: 1800 },
  { name: 'registration_number', label: 'Registration number' },
  { name: 'affiliations', label: 'Affiliation / board', type: 'tags', placeholder: 'CBSE, UGC, AICTE…' },
  { name: 'website', label: 'Website', type: 'url' },
  { name: 'contact_email', label: 'Primary contact email', type: 'email' },
  { name: 'contact_phone', label: 'Primary contact phone', type: 'tel' },
  { name: 'address', label: 'Street address', full: true },
  { name: 'city', label: 'City' },
  { name: 'state', label: 'State' },
  { name: 'pin_code', label: 'Pin code' },
  { name: 'tagline', label: 'Tagline', full: true },
  { name: 'about', label: 'About the institute', type: 'textarea', full: true },
  { name: 'mission', label: 'Mission', type: 'textarea', rows: 2 },
  { name: 'vision', label: 'Vision', type: 'textarea', rows: 2 },
  { name: 'core_values', label: 'Core values', type: 'tags', full: true, placeholder: 'Academic excellence, Inclusivity…' },
  { name: 'total_students', label: 'Total students', type: 'number', nullable: true, min: 0 },
  { name: 'total_teaching_staff', label: 'Total teaching staff', type: 'number', nullable: true, min: 0 },
]

const DEFAULT_JOB = {
  employment_type: 'full_time', work_mode: 'onsite', salary_display: 'range', salary_negotiable: true,
  min_experience_years: 0, vacancies: 1, status: 'open', mandatory_certifications: [],
  preferred_certifications: [], skills: [], key_benefits: [],
}

function JobForm({ job, onSaved, onCancel }) {
  const [v, setV] = useState(job ? { ...DEFAULT_JOB, ...job } : DEFAULT_JOB)
  const [questions, setQuestions] = useState((job?.questions || []).map((q) => q.text))
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k, val) => setV((x) => ({ ...x, [k]: val }))
  const locked = job && job.applications_count > 0

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const payload = buildPayload(v, JOB_FIELDS)
      if (!locked) payload.questions = questions.filter((q) => q.trim()).map((text) => ({ text }))
      if (job) await api.patch(`/jobs/${job.id}/`, payload)
      else await api.post('/jobs/', payload)
      onSaved()
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-6">
      <h2 className="text-2xl font-bold">{job ? 'Edit job' : 'Post a job'}</h2>
      <FormFields fields={JOB_FIELDS} values={v} set={set} />
      <fieldset>
        <legend className="label">Application questions (up to 3)</legend>
        {locked && <p className="mb-2 text-xs text-teal-soft">Questions can’t change once candidates have applied.</p>}
        {[0, 1, 2].map((i) => (
          <input key={i} className="input mb-2" disabled={locked} placeholder={['Why do you want to join our institute?', 'How do you engage a distracted student?', 'Which professional skill do you hope to build here?'][i]} value={questions[i] || ''}
            onChange={(e) => setQuestions((qs) => { const n = [...qs]; n[i] = e.target.value; return n })} />
        ))}
      </fieldset>
      <Alert>{err}</Alert>
      <div className="flex gap-3">
        <button className="btn" disabled={busy}>{busy ? 'Saving…' : job ? 'Save changes' : 'Publish job'}</button>
        <button type="button" className="btn-outline" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

function Applicant({ a, onChanged }) {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState(a.status)
  const [err, setErr] = useState('')
  const d = a.teacher_detail
  const p = d?.profile

  const update = async (s) => {
    setErr('')
    try {
      await api.patch(`/applications/${a.id}/`, { status: s })
      setStatus(s)
      onChanged?.()
    } catch (x) {
      setErr(errMsg(x))
    }
  }
  const toggle = () => {
    if (!open && status === 'applied') update('viewed')
    setOpen(!open)
  }

  return (
    <li className="card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="flex flex-wrap items-center gap-2 font-bold">{a.teacher_name} <MatchBadge score={a.match_score} /></p>
          <p className="text-sm text-teal-soft">{p?.headline} · {p?.total_experience_years} yrs · applied {new Date(a.applied_at).toLocaleDateString('en-IN')}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="sr-only" htmlFor={`st${a.id}`}>Application status</label>
          <select id={`st${a.id}`} className="input w-auto" value={status} onChange={(e) => update(e.target.value)}>
            {APP_STATUS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
          <button className="text-sm font-semibold underline" onClick={toggle}>{open ? 'Hide profile' : 'View profile'}</button>
        </div>
      </div>
      <Alert>{err}</Alert>
      {open && d && (
        <div className="mt-4 space-y-4 border-t border-beige-line pt-4 text-sm">
          <p><b>Contact:</b> {p.email}{p.phone && ` · ${p.phone}`} · {[p.city, p.state].filter(Boolean).join(', ')}</p>
          {p.bio && <p className="whitespace-pre-line">{p.bio}</p>}
          {p.subjects?.length > 0 && <p><b>Subjects:</b> {p.subjects.join(', ')}</p>}
          {p.skills?.length > 0 && <p><b>Skills:</b> {p.skills.join(', ')}</p>}
          {p.intro_video_url && <p><a className="underline" href={p.intro_video_url} target="_blank" rel="noreferrer">Watch introduction video</a></p>}
          <MatchBreakdown breakdown={a.match_breakdown} />
          <AttachedDocuments qualifications={a.attached_qualifications} certifications={a.attached_certifications} />
          {d.qualifications.length > 0 && (
            <div><b>Qualifications</b><ul className="mt-1 space-y-1">{d.qualifications.map((q) => (
              <li key={q.id}>{q.course}{q.specialization && `, ${q.specialization}`} · {q.university} · {q.year_of_passing} {q.marks && `· ${q.marks}`} <VerifyChip status={q.verification_status} />
                {q.marksheet && <> · <a className="underline" href={q.marksheet} target="_blank" rel="noreferrer">Mark sheet</a></>}
                {q.degree_certificate && <> · <a className="underline" href={q.degree_certificate} target="_blank" rel="noreferrer">Certificate</a></>}</li>))}</ul></div>
          )}
          {d.certifications.length > 0 && <p><b>Certifications:</b> {d.certifications.map((c) => c.name).join(', ')}</p>}
          {d.employment.length > 0 && (
            <div><b>Experience</b><ul className="mt-1 space-y-1">{d.employment.map((e) => <li key={e.id}>{e.designation}, {e.institute_name} ({e.start_date} to {e.is_current ? 'present' : e.end_date})</li>)}</ul></div>
          )}
          {a.cover_letter && <div><b>Cover letter</b><p className="mt-1 whitespace-pre-line">{a.cover_letter}</p></div>}
          {a.answers.map((x) => <div key={x.question}><b>{x.question_text}</b><p className="whitespace-pre-line">{x.answer}</p></div>)}
        </div>
      )}
    </li>
  )
}

function Applicants({ job, onBack }) {
  const [apps, setApps] = useState(null)
  const [err, setErr] = useState('')
  const [order, setOrder] = useState('-match_score')
  useEffect(() => { api.get('/applications/', { params: { job: job.id, ordering: order } }).then((r) => setApps(r.data)).catch((x) => setErr(errMsg(x))) }, [job.id, order])
  return (
    <div className="space-y-4">
      <button className="text-sm font-semibold underline" onClick={onBack}>Back to jobs</button>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-bold">Applicants for {job.title}</h2>
        <div className="flex items-center gap-2">
          <label className="text-sm font-semibold" htmlFor="ord">Sort by</label>
          <select id="ord" className="input w-auto" value={order} onChange={(e) => setOrder(e.target.value)}>
            <option value="-match_score">Best match</option>
            <option value="-applied_at">Newest first</option>
          </select>
        </div>
      </div>
      <Alert>{err}</Alert>
      {apps?.length === 0 && <p>No applications yet.</p>}
      <ul className="space-y-3">{apps?.map((a) => <Applicant key={a.id} a={a} />)}</ul>
    </div>
  )
}

function MyJobs({ onEdit, onPost }) {
  const [jobs, setJobs] = useState(null)
  const [viewing, setViewing] = useState(null)
  const [err, setErr] = useState('')
  const load = async () => {
    try {
      let page = 1, all = []
      for (;;) {
        const { data } = await api.get('/jobs/', { params: { page } })
        all = all.concat(data.results)
        if (!data.next) break
        page++
      }
      setJobs(all)
    } catch (x) { setErr(errMsg(x)) }
  }
  useEffect(() => { load() }, [])

  const remove = async (j) => {
    if (!window.confirm(`Delete "${j.title}" and its applications?`)) return
    await api.delete(`/jobs/${j.id}/`)
    load()
  }
  const setStatus = async (j, status) => { await api.patch(`/jobs/${j.id}/`, { status }); load() }

  if (viewing) return <Applicants job={viewing} onBack={() => setViewing(null)} />
  return (
    <div className="space-y-4">
      <Alert>{err}</Alert>
      {jobs === null && !err && <p>Loading…</p>}
      {jobs?.length === 0 && <div className="card"><p className="mb-3">You haven’t posted any jobs yet.</p><button className="btn" onClick={onPost}>Post your first job</button></div>}
      {jobs?.map((j) => (
        <article key={j.id} className="card flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold">{j.title}</h3>
            <p className="text-sm text-teal-soft">{j.city} · {label(EMPLOYMENT_TYPES, j.employment_type)} · {salaryText(j) || 'Salary not listed'}</p>
            <div className="mt-2 flex gap-2"><Chip className={j.status === 'open' ? 'bg-green-100 text-green-900' : ''}>{label(JOB_STATUS, j.status)}</Chip><Chip>{j.applications_count} applicant{j.applications_count === 1 ? '' : 's'}</Chip></div>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <button className="btn" onClick={() => setViewing(j)}>View applicants</button>
            <button className="font-semibold underline" onClick={() => onEdit(j)}>Edit</button>
            {j.status === 'open' ? <button className="font-semibold underline" onClick={() => setStatus(j, 'closed')}>Close</button> : <button className="font-semibold underline" onClick={() => setStatus(j, 'open')}>Reopen</button>}
            <button className="btn-danger" onClick={() => remove(j)}>Delete</button>
          </div>
        </article>
      ))}
    </div>
  )
}

function InstituteProfile() {
  const [p, setP] = useState(null)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.get('/institute/profile/').then((r) => setP(r.data)) }, [])
  if (!p) return <p>Loading…</p>
  const set = (k, v) => setP((x) => ({ ...x, [k]: v }))

  const save = async (e) => {
    e.preventDefault()
    setBusy(true); setErr(''); setMsg('')
    try {
      const r = await api.patch('/institute/profile/', buildPayload(p, INSTITUTE_FIELDS))
      setP(r.data)
      setMsg('Institute profile saved.')
    } catch (x) { setErr(errMsg(x)) } finally { setBusy(false) }
  }

  return (
    <form onSubmit={save} className="space-y-6">
      <section className="card flex flex-wrap items-center gap-6">
        {p.logo && <img src={p.logo} alt="" className="h-20 w-20 rounded-md border border-beige-line bg-white object-contain" />}
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-3"><h2 className="text-2xl font-bold">{p.name}</h2><VerifyChip status={p.verification_status} /></div>
          <p className="text-sm text-teal-soft">Plan: {p.subscription_plan} · Job posts remaining: {p.job_post_quota}</p>
          {p.verification_status !== 'verified' && <p className="mt-1 text-sm">Upload your registration document so we can verify your institute.</p>}
        </div>
        <FileUpload label="Logo" endpoint="/institute/profile/" field="logo" accept="image/*" url={p.logo} onDone={(d) => set('logo', d.logo)} />
        <FileUpload label="Registration document" endpoint="/institute/profile/" field="registration_document" url={p.registration_document} onDone={(d) => set('registration_document', d.registration_document)} />
      </section>
      <section className="card">
        <FormFields fields={INSTITUTE_FIELDS} values={p} set={set} />
      </section>
      <Alert>{err}</Alert>
      <Alert kind="ok">{msg}</Alert>
      <button className="btn" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</button>
    </form>
  )
}

export default function InstituteDashboard() {
  const [tab, setTab] = useState('jobs')
  const [editing, setEditing] = useState(null)
  const [version, setVersion] = useState(0)
  const tabs = [['jobs', 'My jobs'], ['analytics', 'Analytics'], ['post', 'Post a job'], ['profile', 'Institute profile']]
  const go = (t) => { setEditing(null); setTab(t) }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Institute dashboard</h1>
      <div className="flex gap-6 border-b border-beige-line" role="tablist">
        {tabs.map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => go(k)} className={`-mb-px border-b-2 pb-2 font-semibold ${tab === k ? 'border-teal-light' : 'border-transparent text-teal-soft'}`}>{l}</button>
        ))}
      </div>
      {tab === 'jobs' && <MyJobs key={version} onPost={() => go('post')} onEdit={(j) => { setEditing(j); setTab('post') }} />}
      {tab === 'analytics' && <InstituteAnalytics />}
      {tab === 'post' && <JobForm key={editing?.id ?? 'new'} job={editing} onCancel={() => go('jobs')} onSaved={() => { setVersion((n) => n + 1); go('jobs') }} />}
      {tab === 'profile' && <InstituteProfile />}
    </div>
  )
}
