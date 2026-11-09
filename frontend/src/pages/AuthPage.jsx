import { useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth'
import { errMsg } from '../api'
import { Alert } from '../components/ui'

export default function AuthPage() {
  const { user, loading, login, register } = useAuth()
  const nav = useNavigate()
  // The landing page deep-links here: /auth?mode=register&role=institute
  const [params] = useSearchParams()
  const [mode, setMode] = useState(params.get('mode') === 'register' ? 'register' : 'login')
  const [role, setRole] = useState(params.get('role') === 'institute' ? 'institute' : 'teacher')
  const [f, setF] = useState({ email: '', password: '', first_name: '', last_name: '', institute_name: '' })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  if (!loading && user) return <Navigate to="/" replace />

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const u = mode === 'login' ? await login(f.email, f.password) : await register({ ...f, role })
      nav(u.role === 'institute' ? '/institute' : mode === 'register' ? '/profile' : '/jobs')
    } catch (x) {
      setErr(x?.response?.status === 401 ? 'Email or password is incorrect.' : errMsg(x))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-4 py-10 md:grid-cols-2">
      <div>
        <Link to="/" className="font-display text-xl font-bold">Aeterna</Link>
        <h1 className="mt-6 text-4xl font-bold leading-tight md:text-5xl">Let’s brighten our youngsters’ future.</h1>
        <p className="mt-5 max-w-md text-lg leading-relaxed">
          Teachers build one profile and apply anywhere. Schools and colleges post openings and find the right faculty, from KG to PhD.
        </p>
        <blockquote className="mt-10 max-w-md border-l-2 border-teal-light pl-4 font-display text-lg italic">
          Teaching is the greatest act of optimism.
          <footer className="mt-1 font-sans text-sm not-italic text-teal-soft">Colleen Wilcox</footer>
        </blockquote>
      </div>

      <form onSubmit={submit} className="card space-y-4 bg-white/70 p-6">
        <div className="flex gap-6 border-b border-beige-line">
          {[['login', 'Log in'], ['register', 'Create account']].map(([m, t]) => (
            <button type="button" key={m} onClick={() => { setMode(m); setErr('') }} className={`-mb-px border-b-2 pb-2 font-semibold ${mode === m ? 'border-teal-light' : 'border-transparent text-teal-soft'}`}>{t}</button>
          ))}
        </div>

        {mode === 'register' && (
          <fieldset>
            <legend className="label">I am a</legend>
            <div className="grid grid-cols-2 gap-3">
              {[['teacher', 'Teacher / faculty'], ['institute', 'School or institute']].map(([r, t]) => (
                <label key={r} className={`cursor-pointer rounded-md border px-3 py-2 text-center text-sm font-semibold ${role === r ? 'border-teal bg-teal text-beige' : 'border-beige-line'}`}>
                  <input type="radio" className="sr-only" name="role" checked={role === r} onChange={() => setRole(r)} />
                  {t}
                </label>
              ))}
            </div>
          </fieldset>
        )}

        {mode === 'register' && role === 'teacher' && (
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label" htmlFor="fn">First name</label><input id="fn" className="input" required value={f.first_name} onChange={set('first_name')} /></div>
            <div><label className="label" htmlFor="ln">Last name</label><input id="ln" className="input" value={f.last_name} onChange={set('last_name')} /></div>
          </div>
        )}
        {mode === 'register' && role === 'institute' && (
          <div><label className="label" htmlFor="in">Official institute name</label><input id="in" className="input" required value={f.institute_name} onChange={set('institute_name')} /></div>
        )}

        <div><label className="label" htmlFor="em">Email</label><input id="em" type="email" className="input" required value={f.email} onChange={set('email')} autoComplete="email" /></div>
        <div>
          <label className="label" htmlFor="pw">Password</label>
          <input id="pw" type="password" className="input" required minLength={8} value={f.password} onChange={set('password')} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
          {mode === 'register' && <p className="mt-1 text-xs text-teal-soft">At least 8 characters.</p>}
        </div>

        <Alert>{err}</Alert>
        <button className="btn w-full" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}</button>
      </form>
    </div>
  )
}
