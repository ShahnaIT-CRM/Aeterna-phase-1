import { metalGradient, tierOf } from '../tiers'

/** Round medal with a laurel star. Also used big on the public certificate. */
export function TierMedal({ tier, size = 40 }) {
  const t = tierOf(tier)
  const id = `m-${tier}-${size}`
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" className="shrink-0">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={t.light} /><stop offset=".5" stopColor={t.mid} /><stop offset="1" stopColor={t.dark} />
        </linearGradient>
      </defs>
      <circle cx="24" cy="24" r="22" fill={`url(#${id})`} />
      <circle cx="24" cy="24" r="17.5" fill="none" stroke={t.ink} strokeOpacity=".35" strokeWidth="1" />
      <path d="M24 12.5l3.4 7 7.6 1.1-5.5 5.4 1.3 7.6L24 30l-6.8 3.6 1.3-7.6L13 21.6l7.6-1.1z" fill={t.ink} fillOpacity=".78" />
    </svg>
  )
}

/** Prominent tier pill: medal + tier name. size: 'md' | 'lg' */
export default function TierBadge({ tier, name, size = 'md' }) {
  const t = tierOf(tier)
  const big = size === 'lg'
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full font-display font-bold shadow-sm ring-1 ring-black/10 ${big ? 'py-1.5 pl-1.5 pr-5 text-lg' : 'py-1 pl-1 pr-3.5 text-sm'}`}
      style={{ background: metalGradient(t), color: t.ink }}
      title={`${t.metal} tier`}
    >
      <TierMedal tier={tier} size={big ? 40 : 28} />
      {name || t.name}
    </span>
  )
}
