import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MotionConfig, motion } from 'framer-motion'
import useCountUp from '../hooks/useCountUp'

/* ------------------------------------------------------------------ */
/*  Hardcoded content (swap for API data later)                        */
/* ------------------------------------------------------------------ */

const STATS = [
  { target: 100, decimals: 0, suffix: 'K+', label: 'Teachers', note: 'building one profile and applying anywhere' },
  { target: 25, decimals: 0, suffix: 'K+', label: 'Institutes', note: 'from nursery schools to universities' },
  { target: 1.2, decimals: 1, suffix: 'K+', label: 'Active jobs', note: 'open for applications right now' },
]

const INSTITUTES = [
  { name: 'Delhi Public School', city: 'New Delhi', mono: 'DPS' },
  { name: 'St. Xavier’s College', city: 'Mumbai', mono: 'SX' },
  { name: 'Kendriya Vidyalaya', city: 'Pan-India', mono: 'KV' },
  { name: 'The Doon School', city: 'Dehradun', mono: 'DS' },
  { name: 'Christ University', city: 'Bengaluru', mono: 'CU' },
  { name: 'Ryan International', city: 'Mumbai', mono: 'RI' },
  { name: 'National Public School', city: 'Bengaluru', mono: 'NPS' },
  { name: 'Presidency University', city: 'Kolkata', mono: 'PU' },
  { name: 'Podar International', city: 'Mumbai', mono: 'PI' },
  { name: 'Amity University', city: 'Noida', mono: 'AU' },
]

const JOBS = [
  {
    title: 'PGT Physics',
    institute: 'Delhi Public School',
    mono: 'DPS',
    board: 'CBSE',
    city: 'Bangalore',
    type: 'Full-Time',
    mode: 'Onsite',
    salary: '₹7–10 LPA',
    posted: 'Posted 2 days ago',
  },
  {
    title: 'TGT Mathematics',
    institute: 'St. Xavier’s High School',
    mono: 'SX',
    board: 'ICSE',
    city: 'Mumbai',
    type: 'Full-Time',
    mode: 'Onsite',
    salary: '₹5–7 LPA',
    posted: 'Posted 4 days ago',
  },
  {
    title: 'Assistant Professor, Computer Science',
    institute: 'Christ University',
    mono: 'CU',
    board: 'UGC',
    city: 'Hyderabad',
    type: 'Contract',
    mode: 'Hybrid',
    salary: '₹8–12 LPA',
    posted: 'Posted today',
  },
]

const POPULAR_SUBJECTS = ['Physics', 'Mathematics', 'English', 'Computer Science', 'Chemistry']

/* ------------------------------------------------------------------ */
/*  Small building blocks                                              */
/* ------------------------------------------------------------------ */

const EASE = [0.22, 1, 0.36, 1]

/** Fade + slide-up when scrolled into view (once). */
function Reveal({ children, delay = 0, y = 36, className = '' }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.75, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  )
}

const Icon = ({ children, className = 'h-5 w-5' }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
    {children}
  </svg>
)
const BookIcon = (p) => <Icon {...p}><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5v-16Z" /><path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20" /></Icon>
const PinIcon = (p) => <Icon {...p}><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Z" /><circle cx="12" cy="9.5" r="2.5" /></Icon>
const WalletIcon = (p) => <Icon {...p}><path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H19v14H5.5A2.5 2.5 0 0 1 3 16.5v-9Z" /><path d="M16 12h3" /></Icon>

/** Abstract orbit graphic: dashed rings + dots, slowly rotating. */
function Orbit({ className, duration = 80, reverse = false }) {
  return (
    <motion.svg
      viewBox="0 0 400 400"
      fill="none"
      aria-hidden="true"
      className={className}
      animate={{ rotate: reverse ? -360 : 360 }}
      transition={{ duration, repeat: Infinity, ease: 'linear' }}
    >
      <circle cx="200" cy="200" r="190" stroke="#1f3a3f" strokeOpacity=".22" strokeWidth="2" strokeDasharray="2 12" strokeLinecap="round" />
      <circle cx="200" cy="200" r="140" stroke="#1f3a3f" strokeOpacity=".2" strokeWidth="1" />
      <circle cx="200" cy="200" r="90" stroke="#1f3a3f" strokeOpacity=".2" strokeWidth="1" strokeDasharray="6 9" />
      <circle cx="390" cy="200" r="10" fill="#1f3a3f" fillOpacity=".6" />
      <circle cx="101" cy="101" r="6" fill="#1f3a3f" fillOpacity=".45" />
      <circle cx="200" cy="290" r="5" fill="#1f3a3f" fillOpacity=".5" />
      <circle cx="338" cy="338" r="4" fill="#1f3a3f" fillOpacity=".35" />
    </motion.svg>
  )
}

/** Gradient mesh + drifting blobs + orbits. Purely decorative, tints of #1f3a3f on #f5f0e6. */
function HeroBackground() {
  const drift = (x, y, d) => ({
    animate: { x: [0, x, 0], y: [0, y, 0], scale: [1, 1.12, 1] },
    transition: { duration: d, repeat: Infinity, ease: 'easeInOut' },
  })
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div
        className="absolute inset-0"
        style={{
          background: [
            'radial-gradient(55% 45% at 12% 18%, rgba(31,58,63,.16), transparent 70%)',
            'radial-gradient(50% 45% at 90% 12%, rgba(31,58,63,.12), transparent 70%)',
            'radial-gradient(60% 50% at 75% 95%, rgba(31,58,63,.14), transparent 70%)',
            'radial-gradient(45% 40% at 8% 90%, rgba(232,223,204,1), transparent 70%)',
          ].join(','),
        }}
      />
      <motion.div {...drift(70, 50, 16)} className="absolute -left-24 top-10 h-96 w-96 rounded-full bg-teal/20 blur-3xl" />
      <motion.div {...drift(-60, 70, 20)} className="absolute -right-20 top-24 h-[28rem] w-[28rem] rounded-full bg-teal/15 blur-3xl" />
      <motion.div {...drift(40, -50, 24)} className="absolute bottom-[-8rem] left-1/3 h-96 w-[34rem] rounded-full bg-teal/10 blur-3xl" />

      <Orbit className="absolute -right-40 top-1/4 hidden h-[34rem] w-[34rem] md:block" duration={90} />
      <Orbit className="absolute -left-28 bottom-8 hidden h-[22rem] w-[22rem] lg:block" duration={70} reverse />

      {/* soft fade into the next section */}
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-beige" />
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Sections                                                           */
/* ------------------------------------------------------------------ */

function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <motion.header
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: EASE }}
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled ? 'border-b border-teal/10 bg-beige/70 shadow-[0_8px_30px_-12px_rgba(31,58,63,.25)] backdrop-blur-xl' : 'border-b border-transparent bg-transparent'
      }`}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link to="/" className="font-display text-2xl font-bold tracking-tight">Aeterna</Link>
        <nav aria-label="Account" className="flex items-center gap-2 sm:gap-3">
          <Link to="/auth?mode=login" className="btn-outline rounded-full px-3 sm:px-5">Log In</Link>
          <Link to="/auth?mode=register" className="btn rounded-full px-3 sm:px-5">Create Account</Link>
        </nav>
      </div>
    </motion.header>
  )
}

function SearchBar() {
  const nav = useNavigate()
  const [subject, setSubject] = useState('')
  const [city, setCity] = useState('')

  // UI only for now: no backend call. Visitors are sent to sign up so the search can follow once jobs are public.
  const onSubmit = (e) => {
    e.preventDefault()
    nav('/auth?mode=register')
  }

  const field = 'flex flex-1 items-center gap-3 rounded-full px-5 py-3.5 transition focus-within:bg-white/60 focus-within:ring-2 focus-within:ring-teal/30'
  const input = 'w-full bg-transparent text-base text-teal placeholder:text-teal/55 focus:outline-none'

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.9, ease: EASE }}
      className="mx-auto mt-12 w-full max-w-3xl"
    >
      <form
        role="search"
        onSubmit={onSubmit}
        className="flex flex-col gap-2 rounded-[2rem] border border-white/70 bg-white/40 p-2 shadow-[0_24px_60px_-18px_rgba(31,58,63,.4)] backdrop-blur-xl sm:flex-row sm:items-center sm:rounded-full"
      >
        <label className={field}>
          <BookIcon className="h-5 w-5 shrink-0 text-teal/70" />
          <span className="sr-only">Subject</span>
          <input className={input} placeholder="Subject, e.g. Physics" value={subject} onChange={(e) => setSubject(e.target.value)} autoComplete="off" />
        </label>
        <span aria-hidden="true" className="hidden h-8 w-px bg-teal/15 sm:block" />
        <label className={field}>
          <PinIcon className="h-5 w-5 shrink-0 text-teal/70" />
          <span className="sr-only">City</span>
          <input className={input} placeholder="City, e.g. Bangalore" value={city} onChange={(e) => setCity(e.target.value)} autoComplete="off" />
        </label>
        <button className="btn rounded-full px-8 py-3.5 text-base shadow-lg shadow-teal/20 hover:-translate-y-0.5 sm:ml-1">Search jobs</button>
      </form>

      <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-sm">
        <span className="text-teal/70">Popular searches</span>
        {POPULAR_SUBJECTS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setSubject(s)}
            className="rounded-full border border-teal/20 bg-white/30 px-3 py-1 font-semibold backdrop-blur transition hover:border-teal hover:bg-teal hover:text-beige"
          >
            {s}
          </button>
        ))}
      </div>
    </motion.div>
  )
}

function Hero() {
  const words = ['Let’s', 'brighten', 'our', 'youngsters’', 'future']
  return (
    <section className="relative isolate flex min-h-[100svh] flex-col items-center justify-center px-4 pb-24 pt-32 text-center">
      <HeroBackground />

      <h1 className="max-w-5xl text-5xl font-bold leading-[1.04] tracking-tight sm:text-6xl lg:text-7xl xl:text-8xl">
        {words.map((w, i) => (
          <motion.span
            key={w}
            className="inline-block"
            initial={{ opacity: 0, y: 48, filter: 'blur(8px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: 0.8, delay: 0.15 + i * 0.12, ease: EASE }}
          >
            {w}
            {i < words.length - 1 && '\u00A0'}
          </motion.span>
        ))}
      </h1>

      <motion.p
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.8, ease: EASE }}
        className="mt-7 max-w-2xl text-lg leading-relaxed text-teal/85 sm:text-xl"
      >
        Aeterna connects teachers with schools, colleges and institutes across India. Build one profile, carry your verified credentials, and apply anywhere, from KG to PhD.
      </motion.p>

      <SearchBar />
    </section>
  )
}

function Stat({ target, decimals, suffix, label, note }) {
  const [ref, value] = useCountUp(target, { decimals })
  return (
    <div className="px-6 py-10 text-center md:py-12">
      <p className="sr-only">{`${target}${suffix} ${label}`}</p>
      <p ref={ref} aria-hidden="true" className="font-display text-6xl font-bold tabular-nums tracking-tight sm:text-7xl">
        {value}
        {suffix}
      </p>
      <p className="mt-2 text-xl font-semibold">{label}</p>
      <p className="mx-auto mt-1 max-w-[16rem] text-teal/75">{note}</p>
    </div>
  )
}

function Stats() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:py-24">
      <Reveal>
        <h2 className="mx-auto max-w-2xl text-center text-3xl font-bold leading-tight sm:text-4xl">
          India’s teaching community, in one place.
        </h2>
      </Reveal>
      <Reveal delay={0.15} className="mt-12">
        <div className="grid divide-y divide-teal/15 border-y border-teal/15 md:grid-cols-3 md:divide-x md:divide-y-0">
          {STATS.map((s) => (
            <Stat key={s.label} {...s} />
          ))}
        </div>
      </Reveal>
    </section>
  )
}

function InstituteCard({ name, city, mono }) {
  return (
    <li className="group/card flex w-72 shrink-0 cursor-default items-center gap-4 rounded-2xl border border-teal/15 bg-white/50 p-4 backdrop-blur transition duration-300 hover:-translate-y-1.5 hover:border-teal hover:bg-teal hover:text-beige hover:shadow-[0_18px_40px_-14px_rgba(31,58,63,.55)]">
      <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-teal font-display text-base font-bold text-beige transition duration-300 group-hover/card:scale-110 group-hover/card:bg-beige group-hover/card:text-teal">
        {mono}
      </span>
      <span className="min-w-0">
        <span className="block truncate font-display text-lg font-bold">{name}</span>
        <span className="block text-sm text-teal/70 transition group-hover/card:text-beige/80">{city}</span>
      </span>
    </li>
  )
}

function Institutes() {
  return (
    <section className="py-16 sm:py-24">
      <Reveal className="mx-auto max-w-6xl px-4">
        <h2 className="max-w-xl text-3xl font-bold leading-tight sm:text-4xl">Top institutes hiring on Aeterna</h2>
        <p className="mt-3 max-w-xl text-lg text-teal/80">Schools, colleges and universities that post openings and find faculty here.</p>
      </Reveal>

      <Reveal delay={0.15} className="mt-10">
        {/* The track pauses on hover; with reduced motion it becomes a normal horizontally scrollable row. */}
        <div className="group overflow-hidden py-4 [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)] motion-reduce:overflow-x-auto">
          <div className="flex w-max animate-marquee motion-reduce:animate-none group-hover:[animation-play-state:paused]">
            {[0, 1].map((copy) => (
              <ul key={copy} aria-hidden={copy === 1 || undefined} className="flex shrink-0 gap-5 pr-5">
                {INSTITUTES.map((i) => (
                  <InstituteCard key={i.name} {...i} />
                ))}
              </ul>
            ))}
          </div>
        </div>
      </Reveal>
    </section>
  )
}

function JobCard({ job }) {
  return (
    <motion.article
      whileHover={{ y: -10 }}
      transition={{ type: 'spring', stiffness: 300, damping: 22 }}
      className="flex h-full flex-col rounded-3xl border border-white/70 bg-white/40 p-6 shadow-[0_10px_40px_-12px_rgba(31,58,63,.3)] backdrop-blur-xl transition-shadow duration-300 hover:shadow-[0_28px_60px_-14px_rgba(31,58,63,.45)]"
    >
      <div className="flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal font-display text-sm font-bold text-beige">{job.mono}</span>
        <div>
          <p className="font-semibold leading-tight">{job.institute}</p>
          <p className="text-sm text-teal/70">{job.posted}</p>
        </div>
      </div>

      <h3 className="mt-5 text-2xl font-bold leading-snug">{job.title}</h3>

      <ul className="mt-4 flex flex-wrap gap-2 text-sm font-semibold">
        {[job.board, job.type, job.mode].map((t) => (
          <li key={t} className="rounded-full border border-teal/25 bg-white/40 px-3 py-1">{t}</li>
        ))}
      </ul>

      <div className="mt-5 space-y-2 text-teal/85">
        <p className="flex items-center gap-2"><PinIcon className="h-4 w-4" />{job.city}</p>
        <p className="flex items-center gap-2"><WalletIcon className="h-4 w-4" />{job.salary}</p>
      </div>

      <div className="mt-auto pt-7">
        <Link to="/auth?mode=register" className="btn w-full rounded-full py-3 text-base">Apply now</Link>
      </div>
    </motion.article>
  )
}

function LiveJobs() {
  return (
    <section className="relative isolate overflow-hidden py-16 sm:py-24">
      {/* shapes behind the glass cards so the blur has something to blur */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 [mask-image:linear-gradient(to_bottom,transparent,black_25%,black_75%,transparent)]">
        <div className="absolute left-[8%] top-[18%] h-72 w-72 rounded-full bg-teal/25 blur-3xl" />
        <div className="absolute right-[6%] top-[40%] h-80 w-80 rounded-full bg-teal/20 blur-3xl" />
        <div className="absolute bottom-[6%] left-[40%] h-64 w-64 rounded-full bg-teal/15 blur-3xl" />
      </div>

      <div className="mx-auto max-w-6xl px-4">
        <Reveal>
          <h2 className="max-w-xl text-3xl font-bold leading-tight sm:text-4xl">Fresh openings, updated daily</h2>
          <p className="mt-3 max-w-xl text-lg text-teal/80">A small sample of what institutes are hiring for right now.</p>
        </Reveal>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {JOBS.map((job, i) => (
            <Reveal key={job.title} delay={i * 0.12} className="h-full">
              <JobCard job={job} />
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.1} className="mt-12 text-center">
          <Link to="/auth?mode=register" className="btn-outline rounded-full px-8 py-3 text-base">Browse all jobs</Link>
        </Reveal>
      </div>
    </section>
  )
}

function CallToAction() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:py-24">
      <Reveal>
        <div className="relative overflow-hidden rounded-[2rem] bg-teal px-6 py-14 text-center text-beige sm:px-12 sm:py-20">
          <Orbit className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 opacity-30 [filter:invert(1)]" duration={100} />
          <h2 className="relative mx-auto max-w-2xl text-3xl font-bold leading-tight sm:text-5xl">Your next class, or your next teacher, is waiting.</h2>
          <p className="relative mx-auto mt-4 max-w-xl text-lg text-beige/85">Create a free account in a couple of minutes.</p>
          <div className="relative mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link to="/auth?mode=register&role=teacher" className="inline-flex items-center justify-center rounded-full bg-beige px-8 py-3 text-base font-semibold text-teal transition hover:-translate-y-0.5 hover:bg-white">I’m a teacher</Link>
            <Link to="/auth?mode=register&role=institute" className="inline-flex items-center justify-center rounded-full border border-beige px-8 py-3 text-base font-semibold text-beige transition hover:-translate-y-0.5 hover:bg-beige hover:text-teal">I’m hiring for an institute</Link>
          </div>
        </div>
      </Reveal>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-teal/15">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm sm:flex-row">
        <p className="font-display text-xl font-bold">Aeterna</p>
        <nav aria-label="Footer" className="flex gap-6 font-semibold">
          <Link to="/auth?mode=login" className="hover:underline">Log In</Link>
          <Link to="/auth?mode=register" className="hover:underline">Create Account</Link>
        </nav>
        <p className="text-teal/70">© {new Date().getFullYear()} Aeterna</p>
      </div>
    </footer>
  )
}

/* ------------------------------------------------------------------ */

export default function LandingPage() {
  return (
    // reducedMotion="user": framer skips transform animations for visitors who prefer reduced motion
    <MotionConfig reducedMotion="user">
      <div className="min-h-screen overflow-x-hidden bg-beige text-teal">
        <Navbar />
        <main>
          <Hero />
          <Stats />
          <Institutes />
          <LiveJobs />
          <CallToAction />
        </main>
        <Footer />
      </div>
    </MotionConfig>
  )
}
