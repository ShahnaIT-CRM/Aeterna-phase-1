import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const link = ({ isActive }) => `border-b-2 pb-1 text-sm font-semibold ${isActive ? 'border-teal-light' : 'border-transparent hover:border-teal-soft'}`

export default function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-beige-line bg-beige">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <Link to="/" className="font-display text-2xl font-bold tracking-tight">Aeterna</Link>
          <nav className="flex flex-wrap items-center gap-6">
            {user?.role === 'teacher' && (
              <>
                <NavLink to="/jobs" className={link}>Find jobs</NavLink>
                <NavLink to="/applications" className={link}>My applications</NavLink>
                <NavLink to="/courses" className={link}>Learn</NavLink>
                <NavLink to="/profile" className={link}>My profile</NavLink>
              </>
            )}
            {user?.role === 'institute' && <NavLink to="/institute" className={link}>Institute dashboard</NavLink>}
            {user && (
              <>
                <span className="text-sm text-teal-soft">{user.display_name}</span>
                <button className="btn-outline" onClick={() => { logout(); nav('/auth') }}>Log out</button>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8"><Outlet /></main>
      <footer className="border-t border-beige-line py-4 text-center text-sm text-teal-soft">Aeterna – working title</footer>
    </div>
  )
}
