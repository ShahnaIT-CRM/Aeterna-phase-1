import VerificationBadge from './VerificationBadge'
import { VerifyChip } from './ui'

const short = (h = '') => (h ? `${h.slice(0, 6)}…${h.slice(-4)}` : '')
const when = (d) => (d ? new Date(d).toLocaleDateString(undefined, { month: 'short', year: 'numeric' }) : '')

function Card({ q, onEdit, onRemove }) {
  const signed = q.cryptographically_verified
  return (
    <article
      aria-label={`${q.course} from ${q.university_name}`}
      className={`group relative overflow-hidden rounded-2xl border p-5 text-white shadow-[0_10px_40px_-12px_rgba(0,0,0,.6)] backdrop-blur-xl transition duration-300 motion-safe:hover:-translate-y-1 ${
        signed ? 'border-white/30 bg-white/[.14]' : 'border-dashed border-white/25 bg-white/[.07]'
      }`}
    >
      {/* glass sheen; sweeps across signed cards on hover */}
      <span aria-hidden="true" className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/25 via-transparent to-transparent" />
      {signed && <span aria-hidden="true" className="pointer-events-none absolute -inset-y-4 -left-1/2 w-1/3 rotate-12 bg-gradient-to-r from-transparent via-white/25 to-transparent opacity-0 transition duration-700 motion-safe:group-hover:translate-x-[450%] group-hover:opacity-100" />}

      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[.18em] text-white/60">{q.level_label || q.level}</p>
          <h3 className="mt-1 font-display text-xl font-bold leading-snug">{q.course}{q.specialization && <span className="font-normal text-white/80">, {q.specialization}</span>}</h3>
          <p className="mt-1 text-sm text-white/80">{q.university_name}</p>
        </div>
        {/* contactless-style chip */}
        <svg viewBox="0 0 40 30" className="h-8 w-10 shrink-0 opacity-80" aria-hidden="true">
          <rect x="1" y="1" width="38" height="28" rx="6" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M1 10h12v10H1M27 10h12v10H27M13 1v28M27 1v28" fill="none" stroke="currentColor" strokeWidth="1.2" />
        </svg>
      </div>

      <div className="relative mt-5 flex flex-wrap items-end justify-between gap-3">
        <div className="text-xs text-white/70">
          <p>Class of {q.year_of_passing}{q.marks && ` · ${q.marks}`}</p>
          {signed
            ? <p className="mt-0.5 font-mono">sha256 {short(q.document_sha256)} · signed {when(q.signed_at)}</p>
            : <p className="mt-0.5">{q.verification_status === 'rejected' ? 'Not confirmed. Check the details and save again.' : `Awaiting signature from ${q.university_name}`}</p>}
        </div>
        {signed
          ? <VerificationBadge q={q} tone="glass" />
          : <span className="rounded-full bg-white/90 px-1"><VerifyChip status={q.verification_status} /></span>}
      </div>

      <div className="relative mt-4 flex gap-4 border-t border-white/15 pt-3 text-xs font-semibold">
        <button className="underline decoration-white/40 underline-offset-2 hover:decoration-white" onClick={() => onEdit(q)}>Edit</button>
        <button className="text-red-200 hover:underline" onClick={() => onRemove(q.id)}>Delete</button>
      </div>
    </article>
  )
}

/** Apple-Wallet style glass cards on a deep gradient. Signed degrees shimmer; pending ones are dashed. */
export default function QualificationWallet({ items, edit, remove }) {
  return (
    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#0f2327] via-[#1f3a3f] to-[#35656d] p-5 sm:p-7">
      <span aria-hidden="true" className="pointer-events-none absolute -left-16 -top-16 h-64 w-64 rounded-full bg-[#d4a937]/30 blur-3xl" />
      <span aria-hidden="true" className="pointer-events-none absolute -bottom-20 right-0 h-72 w-72 rounded-full bg-[#5ec4b6]/25 blur-3xl" />
      <div className="relative grid gap-5 md:grid-cols-2">
        {items.map((q) => <Card key={q.id} q={q} onEdit={edit} onRemove={remove} />)}
      </div>
    </div>
  )
}
