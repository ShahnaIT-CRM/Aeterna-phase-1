import { Chip, VerifyChip } from './ui'
import { QualificationBadge } from './VerificationBadge'

const tier = (s) => (s >= 75 ? 'bg-green-100 text-green-900' : s >= 50 ? 'bg-yellow-100 text-yellow-900' : 'bg-red-100 text-red-900')
const FACTOR_LABELS = { subject: 'Subject', experience: 'Experience', location: 'Location', salary: 'Salary' }

/** Overall 0-100 match score as a coloured chip. Renders nothing when there is no score. */
export function MatchBadge({ score }) {
  if (score == null) return null
  const n = Math.round(score)
  return <Chip className={tier(n)}>{n}% match</Chip>
}

/** Per-factor explanation of a match score (institute view). */
export function MatchBreakdown({ breakdown }) {
  const factors = breakdown?.factors
  if (!factors) return null
  return (
    <div>
      <b>Why this score</b>
      <ul className="mt-2 space-y-3">
        {Object.entries(factors).map(([key, f]) => (
          <li key={key}>
            <div className="flex items-center justify-between gap-3">
              <span className="font-semibold">{FACTOR_LABELS[key] || key}</span>
              <span className="text-xs text-teal-soft">{f.points} of {f.weight} points</span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-beige-dark" role="img" aria-label={`${FACTOR_LABELS[key] || key}: ${f.score}% fit`}>
              <div className="h-full bg-teal-light" style={{ width: `${f.score}%` }} />
            </div>
            <p className="mt-1 text-xs text-teal-soft">{f.reason}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}

const FileLink = ({ href, children }) => <a className="underline" href={href} target="_blank" rel="noreferrer">{children}</a>

/** Degrees and certificates that were auto-attached to an application. */
export function AttachedDocuments({ qualifications = [], certifications = [] }) {
  const empty = qualifications.length === 0 && certifications.length === 0
  return (
    <div>
      <b>Documents attached to this application</b>
      {empty && <p className="mt-1 text-teal-soft">The candidate hadn’t uploaded any degree or certificate files when they applied.</p>}
      <ul className="mt-1 space-y-1">
        {qualifications.map((q) => (
          <li key={`q${q.id}`}>
            {q.course}{q.specialization && `, ${q.specialization}`} · {q.university_name} <QualificationBadge q={q} />
            {q.degree_certificate && <> · <FileLink href={q.degree_certificate}>Degree certificate</FileLink></>}
            {q.marksheet && <> · <FileLink href={q.marksheet}>Mark sheet</FileLink></>}
          </li>
        ))}
        {certifications.map((c) => (
          <li key={`c${c.id}`}>
            {c.name}{c.issuing_organization && ` · ${c.issuing_organization}`} <VerifyChip status={c.verification_status} />
            {c.document && <> · <FileLink href={c.document}>Certificate</FileLink></>}
          </li>
        ))}
      </ul>
    </div>
  )
}
