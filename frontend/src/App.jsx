import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import AuthPage from './pages/AuthPage'
import JobFeed from './pages/JobFeed'
import MyApplications from './pages/MyApplications'
import TeacherProfile from './pages/TeacherProfile'
import InstituteDashboard from './pages/InstituteDashboard'

function Home() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/auth" replace />
  return <Navigate to={user.role === 'institute' ? '/institute' : '/jobs'} replace />
}

function Guard({ role, children }) {
  const { user, loading } = useAuth()
  if (loading) return <p>Loading…</p>
  if (!user) return <Navigate to="/auth" replace />
  if (user.role !== role) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/auth" element={<AuthPage />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/jobs" element={<Guard role="teacher"><JobFeed /></Guard>} />
        <Route path="/applications" element={<Guard role="teacher"><MyApplications /></Guard>} />
        <Route path="/profile" element={<Guard role="teacher"><TeacherProfile /></Guard>} />
        <Route path="/institute" element={<Guard role="institute"><InstituteDashboard /></Guard>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
