import { useEffect, useState } from 'react'
import api, { errMsg } from '../api'
import MeritProgress from '../components/MeritProgress'
import QualificationWallet from '../components/QualificationWallet'
import ShareProfile from '../components/ShareProfile'
import TierBadge from '../components/TierBadge'
import { Alert, Chip, CrudSection, FileUpload, FormFields, VerifyChip, buildPayload } from '../components/ui'
import {
  COURSE_TYPES, DESIGNATIONS, EMPLOYMENT_TYPES, GENDERS, GRADING, INSTITUTE_TYPES, NOTICE,
  QUAL_LEVELS, VISIBILITY, WORK_STATUS, WORK_STATUS_STYLE, label,
} from '../constants'

const QUALIFICATION_FIELDS = [
  { name: 'level', label: 'Qualification', type: 'select', options: QUAL_LEVELS, required: true },
  { name: 'course', label: 'Course / degree', required: true, datalist: ['B.A.', 'B.Sc.', 'B.Com', 'B.Ed.', 'B.El.Ed.', 'D.El.Ed.', 'B.Tech', 'M.A.', 'M.Sc.', 'M.Com', 'M.Ed.', 'M.Tech', 'Ph.D.'], hint: 'Pick a suggestion or type your own.' },
  { name: 'specialization', label: 'Specialization', placeholder: 'e.g. Physics, English' },
  { name: 'university', label: 'University', type: 'university', required: true, full: true, hint: 'Only universities verified by Aeterna are listed. They will be asked to sign your degree.' },
  { name: 'year_of_passing', label: 'Year of passing', type: 'number', required: true, min: 1950 },
  { name: 'course_type', label: 'Course type', type: 'select', options: COURSE_TYPES },
  { name: 'grading_system', label: 'Grading system', type: 'select', options: GRADING },
  { name: 'marks', label: 'Marks / grade', placeholder: 'e.g. 85 or 3.8' },
  { name: 'marksheet', label: 'Mark sheet', type: 'file', required: true, accept: '.pdf,.jpg,.jpeg,.png', hint: 'PDF, JPG or PNG, up to 5 MB.' },
  { name: 'degree_certificate', label: 'Degree certificate', type: 'file', required: true, accept: '.pdf,.jpg,.jpeg,.png', hint: 'PDF, JPG or PNG, up to 5 MB. This exact file is what your university signs.' },
]

const CERT_FIELDS = [
  { name: 'name', label: 'Certification', required: true, datalist: ['CTET', 'State TET', 'NET', 'SET', 'TEFL', 'TESOL', 'Google Certified Educator'] },
  { name: 'issuing_organization', label: 'Issuing organization' },
  { name: 'date_of_issue', label: 'Date of issue', type: 'date', nullable: true },
  { name: 'valid_until', label: 'Valid until', type: 'date', nullable: true },
  { name: 'document', label: 'Supporting document', type: 'file' },
]

const EMPLOYMENT_FIELDS = [
  { name: 'is_current', label: 'I currently work here', type: 'checkbox', full: true },
  { name: 'institute_name', label: 'Institute name', required: true },
  { name: 'institute_type', label: 'Institute type', type: 'select', options: INSTITUTE_TYPES },
  { name: 'designation', label: 'Designation', required: true, datalist: DESIGNATIONS },
  { name: 'employment_type', label: 'Employment type', type: 'select', options: EMPLOYMENT_TYPES },
  { name: 'boards', label: 'Boards / curriculum', type: 'tags', placeholder: 'CBSE, IB…' },
  { name: 'subjects', label: 'Subjects taught', type: 'tags' },
  { name: 'grades', label: 'Grades taught', type: 'tags', placeholder: 'Grades 6-8, Grades 9-10…' },
  { name: 'start_date', label: 'From', type: 'date', required: true },
  { name: 'end_date', label: 'To', type: 'date', nullable: true, hideIf: (v) => v.is_current },
  { name: 'description', label: 'Describe your work', type: 'textarea', full: true, hint: 'Key responsibilities, key achievements, skills used (e.g. SMART Board, LMS, counselling).' },
  { name: 'achievements', label: 'Awards and recognition', type: 'textarea', full: true, rows: 2 },
]

export default function TeacherProfile() {
  const [p, setP] = useState(null)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.get('/teacher/profile/').then((r) => setP(r.data)) }, [])
  if (!p) return <p>Loading…</p>

  const set = (k, v) => setP((x) => ({ ...x, [k]: v }))
  const refreshCompleteness = () => api.get('/teacher/profile/').then((r) => setP((x) => ({ ...x, completeness: r.data.completeness, merit: r.data.merit })))
  const words = (p.bio || '').trim().split(/\s+/).filter(Boolean).length

  const groups = [
    {
      title: 'About you',
      fields: [
        { name: 'first_name', label: 'First name', required: true },
        { name: 'middle_name', label: 'Middle name' },
        { name: 'last_name', label: 'Last name' },
        { name: 'date_of_birth', label: 'Date of birth', type: 'date', nullable: true },
        { name: 'gender', label: 'Gender', type: 'select', options: GENDERS },
        { name: 'phone', label: 'Phone number', type: 'tel' },
        { name: 'whatsapp_number', label: 'WhatsApp number (if different)', type: 'tel' },
        { name: 'headline', label: 'Headline', full: true, placeholder: 'Experienced Biology teacher with a PhD, 10+ years in CBSE', hint: 'One line that tells recruiters who you are.' },
        { name: 'bio', label: 'Summary', type: 'textarea', full: true, rows: 6, hint: `${words} / 500 words. Your roles, experience, and why you teach.` },
      ],
    },
    {
      title: 'Where you are and where you could go',
      fields: [
        { name: 'address', label: 'Street address', full: true },
        { name: 'city', label: 'City' },
        { name: 'state', label: 'State' },
        { name: 'pin_code', label: 'Pin code' },
        { name: 'willing_to_relocate', label: 'Willing to relocate', type: 'checkbox' },
        { name: 'preferred_cities', label: 'Preferred cities or states', type: 'tags', hideIf: (v) => !v.willing_to_relocate },
        { name: 'relocation_notice_days', label: 'How soon can you relocate?', type: 'select', options: NOTICE, nullable: true, hideIf: (v) => !v.willing_to_relocate },
      ],
    },
    {
      title: 'Teaching profile',
      fields: [
        { name: 'total_experience_years', label: 'Total experience (years)', type: 'number', min: 0 },
        { name: 'employment_status', label: 'Current status', type: 'select', options: WORK_STATUS },
        { name: 'subjects', label: 'Subjects', type: 'tags', placeholder: 'Physics, Mathematics…' },
        { name: 'skills', label: 'Skills', type: 'tags', placeholder: 'Flipped classroom, Google Suite, Moodle…' },
        { name: 'languages', label: 'Languages', type: 'tags', placeholder: 'English, Hindi, Kannada…' },
        { name: 'preferred_job_types', label: 'Preferred job types', type: 'tags', placeholder: 'full_time, part_time…' },
        { name: 'preferred_grades', label: 'Preferred levels', type: 'tags', placeholder: 'Middle school, PGT…' },
        { name: 'salary_expectation', label: 'Expected salary (₹ per year)', type: 'number', nullable: true, min: 0 },
        { name: 'salary_negotiable', label: 'Salary is negotiable', type: 'checkbox' },
      ],
    },
    {
      title: 'Visibility, video and links',
      fields: [
        { name: 'visibility', label: 'Profile visibility', type: 'select', options: VISIBILITY, tip: 'Selective: visible only to recruiters you apply to.' },
        { name: 'intro_video_url', label: 'Introduction video link', type: 'url', hint: 'A 1-3 minute video about you and your teaching style. Use a well-lit space with no background noise.' },
        { name: 'linkedin_url', label: 'LinkedIn', type: 'url' },
        { name: 'website_url', label: 'Website or blog', type: 'url' },
        { name: 'youtube_url', label: 'YouTube channel', type: 'url' },
      ],
    },
  ]
  const allFields = groups.flatMap((g) => g.fields)

  const save = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    setMsg('')
    try {
      const r = await api.patch('/teacher/profile/', buildPayload(p, allFields))
      setP(r.data)
      setMsg('Profile saved.')
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <section className="card flex flex-wrap items-center gap-6">
        {p.photo ? <img src={p.photo} alt="" className="h-24 w-24 rounded-full border border-beige-line bg-white object-cover" /> : <div className="flex h-24 w-24 items-center justify-center rounded-full bg-beige-dark text-2xl font-bold">{p.first_name?.[0]}</div>}
        <div className="min-w-[14rem] flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold">{[p.first_name, p.last_name].filter(Boolean).join(' ')}</h1>
            {p.merit && <TierBadge tier={p.merit.tier} name={p.merit.tier_name} size="lg" />}
            <Chip className={WORK_STATUS_STYLE[p.employment_status]}>{label(WORK_STATUS, p.employment_status)}</Chip>
          </div>
          {p.merit && <p className="mt-1 font-display text-lg font-semibold leading-snug">{p.merit.headline}</p>}
          <p className="text-teal-soft">{p.headline || 'Add a headline so recruiters know who you are.'}</p>
          <div className="mt-3 max-w-sm">
            <div className="flex justify-between text-xs font-semibold"><span>Profile completeness</span><span>{p.completeness}%</span></div>
            <div className="mt-1 h-2 rounded-full bg-beige-dark"><div className="h-2 rounded-full bg-teal-light" style={{ width: `${p.completeness}%` }} /></div>
          </div>
        </div>
        <FileUpload label="Professional photo (white background)" endpoint="/teacher/profile/" field="photo" accept="image/*" url={p.photo} onDone={(d) => { set('photo', d.photo); refreshCompleteness() }} />
      </section>

      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <MeritProgress merit={p.merit} />
        <ShareProfile teacherId={p.id} visibility={p.visibility} onVisibility={(v) => set('visibility', v)} />
      </div>

      <form onSubmit={save} className="space-y-6">
        {groups.map((g) => (
          <section key={g.title} className="card">
            <h2 className="mb-4 text-xl font-bold">{g.title}</h2>
            <FormFields fields={g.fields} values={p} set={set} />
          </section>
        ))}
        <Alert>{err}</Alert>
        <Alert kind="ok">{msg}</Alert>
        <button className="btn" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</button>
      </form>

      <CrudSection
        title="Qualifications" hint="Choose your university, upload both documents, and it signs your degree. Signed degrees earn the green badge and count towards your merit score."
        endpoint="/teacher/qualifications/" fields={QUALIFICATION_FIELDS} onChange={refreshCompleteness}
        emptyText="No qualifications yet. Add your highest degree first."
        renderItems={(props) => <QualificationWallet {...props} />}
        summary={() => null}
      />

      <CrudSection
        title="Employment" hint="Add each role you have held."
        endpoint="/teacher/employment/" fields={EMPLOYMENT_FIELDS} onChange={refreshCompleteness}
        emptyText="No employment history yet."
        summary={(e) => (
          <>
            <p className="font-semibold">{e.designation} at {e.institute_name}{e.is_current && ' (current)'}</p>
            <p className="text-teal-soft">{e.start_date} to {e.is_current ? 'present' : e.end_date || '—'} · {label(EMPLOYMENT_TYPES, e.employment_type)}</p>
            {e.subjects?.length > 0 && <p>{e.subjects.join(', ')}</p>}
          </>
        )}
      />

      <CrudSection
        title="Certifications" hint="CTET, NET, TEFL, workshops and other certificates."
        endpoint="/teacher/certifications/" fields={CERT_FIELDS}
        emptyText="No certifications added."
        summary={(c) => (
          <>
            <p className="font-semibold">{c.name}</p>
            <p className="text-teal-soft">{c.issuing_organization}{c.date_of_issue && ` · issued ${c.date_of_issue}`}{c.valid_until && ` · valid until ${c.valid_until}`}</p>
            <div className="mt-1"><VerifyChip status={c.verification_status} /></div>
          </>
        )}
      />
    </div>
  )
}
