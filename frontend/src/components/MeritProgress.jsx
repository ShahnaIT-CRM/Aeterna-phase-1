import TierBadge from './TierBadge'
import { TIER_FLOORS, metalGradient, tierOf } from '../tiers'

const PARTS = [['university', 'University ranking'], ['degree', 'Degree level'], ['certification', 'Certifications'], ['experience', 'Experience']]

/** The dopamine loop: where you are, exactly how far the next tier is, and what to do about it. */
export default function MeritProgress({ merit }) {
  if (!merit) return null
  const { score, tier, next_tier: next, next_steps: steps = [], breakdown = {}, max_points: max = {} } = merit
  const t = tierOf(tier)
  const nt = next ? tierOf(next.next_tier) : null

  return (
    <section className="card" aria-labelledby="merit-h">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="merit-h" className="text-xl font-bold">Your merit score</h2>
          <p className="text-sm text-teal-soft">Counts only degrees signed by their university and certificates verified by Aeterna.</p>
        </div>
        <p className="font-display text-4xl font-bold leading-none">{score}<span className="text-lg text-teal-soft"> / 100</span></p>
      </div>

      {/* Track with tier markers */}
      <div className="mt-5">
        <div
          className="relative h-3 rounded-full bg-beige-dark" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={score}
          aria-label={next ? `${score} of 100. ${next.points_needed} points to ${next.next_tier_name}` : `${score} of 100. Top tier reached`}
        >
          <div className="h-3 rounded-full transition-[width] duration-700 motion-reduce:transition-none" style={{ width: `${Math.max(score, 2)}%`, background: metalGradient(t) }} />
          {TIER_FLOORS.filter(([, f]) => f > 0).map(([k, f]) => (
            <span key={k} aria-hidden="true" className="absolute top-0 h-3 w-0.5 bg-teal/40" style={{ left: `${f}%` }} />
          ))}
        </div>
        <div className="relative mt-1 h-4 text-[11px] font-semibold text-teal-soft" aria-hidden="true">
          {TIER_FLOORS.filter(([, f]) => f > 0).map(([k, f]) => <span key={k} className="absolute -translate-x-1/2" style={{ left: `${f}%` }}>{f}</span>)}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <TierBadge tier={tier} />
        {next ? (
          <p className="text-sm">
            <strong>{next.points_needed} more point{next.points_needed === 1 ? '' : 's'}</strong> to reach{' '}
            <span className="font-bold" style={{ color: nt.dark }}>{next.next_tier_name}</span>
          </p>
        ) : (
          <p className="text-sm font-semibold">You hold the highest tier. Keep your credentials current.</p>
        )}
      </div>

      {steps.length > 0 && (
        <div className="mt-5">
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-teal-soft">{next ? 'How to get there' : 'Ways to strengthen your profile'}</h3>
          <ul className="space-y-2">
            {steps.map((s) => (
              <li key={s.action} className="flex items-center justify-between gap-3 rounded-md border border-beige-line bg-white/60 px-3 py-2 text-sm">
                <span>{s.action}</span>
                <span className="shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-xs font-bold text-green-900">+{s.points}{s.points >= 20 ? ' or more' : ''}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <details className="mt-4 text-sm">
        <summary className="cursor-pointer font-semibold">How your score is made up</summary>
        <ul className="mt-3 space-y-2">
          {PARTS.map(([k, lab]) => (
            <li key={k}>
              <div className="flex justify-between text-xs font-semibold"><span>{lab}</span><span>{breakdown[k] ?? 0} / {max[k]}</span></div>
              <div className="mt-1 h-1.5 rounded-full bg-beige-dark"><div className="h-1.5 rounded-full bg-teal-light" style={{ width: `${((breakdown[k] ?? 0) / (max[k] || 1)) * 100}%` }} /></div>
            </li>
          ))}
        </ul>
      </details>
    </section>
  )
}
