import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { publicApi } from '../api'
import { TierMedal } from '../components/TierBadge'
import VerificationBadge from '../components/VerificationBadge'
import { linkedInShareUrl } from '../components/ShareProfile'
import { metalGradient, tierOf } from '../tiers'

const year = (d) => (d ? new Date(d).getFullYear() : '')

function Corner({ className, color }) {
  return (
    <svg viewBox="0 0 60 60" className={`absolute h-12 w-12 sm:h-16 sm:w-16 ${className}`} aria-hidden="true" fill="none" stroke={color} strokeWidth="1.5">
      <path d="M2 58V2h56" /><path d="M10 50V10h40" strokeOpacity=".6" /><circle cx="10" cy="10" r="3" fill={color} stroke="none" />
    </svg>
  )
}

function ScoreRing({ score, t }) {
  const r = 34
  const c = 2 * Math.PI * r
  return (
    <div className="relative h-24 w-24" role="img" aria-label={`Merit score ${score} out of 100`}>
      <svg viewBox="0 0 80 80" className="-rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#e8dfcc" strokeWidth="6" />
        <circle cx="40" cy="40" r={r} fill="none" stroke={t.mid} strokeWidth="6" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-2xl font-bold leading-none text-teal">{score}</span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-teal-soft">of 100</span>
      </div>
    </div>
  )
}

/** /t/:teacher_id. A shareable, luxury-certificate view of one teacher. Public: no login, no private data. */
export default function PublicProfile() {
  const { teacher_id: id } = useParams()
  const [d, setD] = useState(null)
  const [missing, setMissing] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    publicApi.get(`/public/teachers/${id}/`).then((r) => setD(r.data)).catch(() => setMissing(true))
  }, [id])
  useEffect(() => { if (d) document.title = `${d.name} · ${d.merit.tier_name} | Aeterna` }, [d])

  const shell = 'min-h-screen bg-[#f3ecdc] px-3 py-8 sm:px-6 sm:py-14 print:bg-white print:p-0'
  if (missing) {
    return (
      <div className={shell}>
        <div className="mx-auto max-w-lg rounded-lg border border-beige-line bg-[#fffdf7] p-10 text-center">
          <h1 className="text-2xl font-bold">This profile is not available</h1>
          <p className="mt-2 text-teal-soft">It may be private, or the link may be wrong.</p>
          <a href="/" className="btn mt-6">Go to Aeterna</a>
        </div>
      </div>
    )
  }
  if (!d) return <div className={shell} aria-busy="true" />

  const t = tierOf(d.merit.tier)
  const url = window.location.href
  const copy = async () => {
    try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000) } catch { window.prompt('Copy this link', url) }
  }

  return (
    <div className={shell}>
      <main className="relative mx-auto max-w-3xl bg-[#fffdf7] p-3 shadow-[0_30px_80px_-30px_rgba(31,58,63,.45)] sm:p-5 print:shadow-none">
        {/* double rule frame */}
        <div className="relative border-2 px-5 pb-10 pt-12 sm:px-14 sm:pt-16" style={{ borderColor: t.mid }}>
          <div className="pointer-events-none absolute inset-1.5 border" style={{ borderColor: t.mid, opacity: 0.55 }} aria-hidden="true" />
          <Corner className="left-2 top-2" color={t.dark} />
          <Corner className="right-2 top-2 rotate-90" color={t.dark} />
          <Corner className="bottom-2 left-2 -rotate-90" color={t.dark} />
          <Corner className="bottom-2 right-2 rotate-180" color={t.dark} />

          <header className="text-center">
            <p className="font-display text-sm font-bold uppercase tracking-[.5em] text-teal">Aeterna</p>
            <p className="mt-1 text-[11px] font-semibold uppercase tracking-[.35em] text-teal-soft">Certificate of Educator Merit</p>
            <div className="mx-auto mt-6 flex justify-center"><TierMedal tier={d.merit.tier} size={96} /></div>
          </header>

          <section className="mt-8 text-center">
            <p className="text-sm italic text-teal-soft">This certifies the standing of</p>
            {d.photo && <img src={d.photo} alt="" className="mx-auto mt-4 h-20 w-20 rounded-full border-2 object-cover" style={{ borderColor: t.mid }} />}
            <h1 className="mt-3 font-display text-4xl font-bold leading-tight text-teal sm:text-5xl">{d.name}</h1>
            <p className="mt-3 inline-block bg-clip-text font-display text-2xl font-bold text-transparent sm:text-3xl" style={{ backgroundImage: metalGradient(t) }}>
              {d.merit.tier_name}
            </p>
            <div className="mx-auto mt-3 h-px w-40" style={{ background: `linear-gradient(90deg, transparent, ${t.mid}, transparent)` }} aria-hidden="true" />
            <p className="mx-auto mt-4 max-w-xl font-display text-lg leading-snug text-teal">{d.merit.headline}</p>
            {d.headline && <p className="mx-auto mt-2 max-w-xl text-sm text-teal-soft">{d.headline}</p>}
            <p className="mt-2 text-sm text-teal-soft">{[d.city, d.state].filter(Boolean).join(', ')}{d.total_experience_years ? ` · ${d.total_experience_years} years of teaching` : ''}</p>
          </section>

          <div className="mt-8 flex justify-center"><ScoreRing score={d.merit.score} t={t} /></div>

          <section className="mt-10" aria-labelledby="pq">
            <h2 id="pq" className="border-b pb-1 text-center text-xs font-bold uppercase tracking-[.3em] text-teal-soft" style={{ borderColor: t.mid }}>Verified qualifications</h2>
            {d.qualifications.length === 0 ? (
              <p className="mt-4 text-center text-sm text-teal-soft">No degrees have been signed by their universities yet.</p>
            ) : (
              <ul className="mt-4 space-y-4">
                {d.qualifications.map((q) => (
                  <li key={q.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-white/70 px-4 py-3" style={{ borderColor: '#e4dac1' }}>
                    <div>
                      <p className="font-display text-lg font-bold text-teal">{q.course}{q.specialization && `, ${q.specialization}`}</p>
                      <p className="text-sm text-teal-soft">{q.university_name}{q.nirf_rank ? ` · NIRF #${q.nirf_rank}` : ''} · {q.year_of_passing}</p>
                    </div>
                    <VerificationBadge q={q} anonymous />
                  </li>
                ))}
              </ul>
            )}
          </section>

          {d.certifications.length > 0 && (
            <section className="mt-8" aria-labelledby="pc">
              <h2 id="pc" className="border-b pb-1 text-center text-xs font-bold uppercase tracking-[.3em] text-teal-soft" style={{ borderColor: t.mid }}>Certifications</h2>
              <ul className="mt-3 flex flex-wrap justify-center gap-2">
                {d.certifications.map((c, i) => <li key={i} className="rounded-full border px-3 py-1 text-sm font-semibold text-teal" style={{ borderColor: t.mid }}>{c.name}</li>)}
              </ul>
            </section>
          )}

          {d.employment.length > 0 && (
            <section className="mt-8" aria-labelledby="pe">
              <h2 id="pe" className="border-b pb-1 text-center text-xs font-bold uppercase tracking-[.3em] text-teal-soft" style={{ borderColor: t.mid }}>Experience</h2>
              <ul className="mt-3 space-y-1 text-center text-sm">
                {d.employment.map((e, i) => (
                  <li key={i}><strong>{e.designation}</strong>, {e.institute_name} <span className="text-teal-soft">({year(e.start_date)}–{e.is_current ? 'present' : year(e.end_date)})</span></li>
                ))}
              </ul>
            </section>
          )}

          {d.subjects?.length > 0 && <p className="mt-8 text-center text-sm text-teal-soft">Subjects: {d.subjects.join(' · ')}</p>}

          <footer className="mt-10 text-center">
            <p className="mx-auto max-w-md text-xs leading-relaxed text-teal-soft">
              Each degree above is digitally signed by the issuing university (Ed25519). Select a green badge to re-check the signature and the document fingerprint live.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-3 print:hidden">
              <a className="btn" href={linkedInShareUrl(url)} target="_blank" rel="noreferrer">
                <svg viewBox="0 0 24 24" className="mr-2 h-4 w-4" fill="currentColor" aria-hidden="true"><path d="M4.98 3.5a2.5 2.5 0 11-.02 5 2.5 2.5 0 01.02-5zM3 9.75h4V21H3zM9.75 9.75h3.83v1.54h.05c.53-.95 1.84-1.95 3.78-1.95 4.04 0 4.79 2.66 4.79 6.1V21h-4v-4.9c0-1.17-.02-2.67-1.63-2.67-1.63 0-1.88 1.27-1.88 2.58V21h-4z" /></svg>
                Share to LinkedIn
              </a>
              <button className="btn-outline" onClick={copy}>{copied ? 'Link copied ✓' : 'Copy link'}</button>
            </div>
          </footer>
        </div>
      </main>
      <p className="mt-5 text-center text-xs text-teal-soft print:hidden">Issued on <a className="underline" href="/">Aeterna</a></p>
    </div>
  )
}
