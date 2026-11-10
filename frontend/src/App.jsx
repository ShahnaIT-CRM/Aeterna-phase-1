import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import AuthPage from './pages/AuthPage'
import JobFeed from './pages/JobFeed'
import MyApplications from './pages/MyApplications'
import TeacherProfile from './pages/TeacherProfile'
import InstituteDashboard from './pages/InstituteDashboard'
import Courses from './pages/Courses'
import CourseDetail from './pages/CourseDetail'
import UniversityDashboard from './pages/UniversityDashboard'

// Lazy-loaded so logged-in users never download framer-motion / landing assets.
const LandingPage = lazy(() => import('./pages/LandingPage'))
const PublicProfile = lazy(() => import('./pages/PublicProfile'))

const dashboardFor = (user) => ({ institute: '/institute', university: '/university' }[user.role] || '/jobs')
const Blank = () => <div className="min-h-screen bg-beige" aria-busy="true" />

// "/" – public landing for visitors, straight to the right dashboard for signed-in users.
function Root() {
  const { user, loading } = useAuth()
  if (loading) return <Blank />
  if (user) return <Navigate to={dashboardFor(user)} replace />
  return (
    <Suspense fallback={<Blank />}>
      <LandingPage />
    </Suspense>
  )
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
      {/* Full-bleed public pages (no Layout chrome) */}
      <Route path="/" element={<Root />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/t/:teacher_id" element={<Suspense fallback={<Blank />}><PublicProfile /></Suspense>} />

      <Route element={<Layout />}>
        <Route path="/jobs" element={<Guard role="teacher"><JobFeed /></Guard>} />
        <Route path="/applications" element={<Guard role="teacher"><MyApplications /></Guard>} />
        <Route path="/courses" element={<Guard role="teacher"><Courses /></Guard>} />
        <Route path="/courses/:id" element={<Guard role="teacher"><CourseDetail /></Guard>} />
        <Route path="/profile" element={<Guard role="teacher"><TeacherProfile /></Guard>} />
        <Route path="/institute" element={<Guard role="institute"><InstituteDashboard /></Guard>} />
        <Route path="/university" element={<Guard role="university"><UniversityDashboard /></Guard>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
