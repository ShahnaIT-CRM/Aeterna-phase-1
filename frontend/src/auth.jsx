import { createContext, useContext, useEffect, useState } from 'react'
import api from './api'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!localStorage.getItem('access'))

  useEffect(() => {
    if (!localStorage.getItem('access')) return
    api.get('/auth/me/').then((r) => setUser(r.data)).catch(() => localStorage.clear()).finally(() => setLoading(false))
  }, [])

  const saveTokens = (d) => {
    localStorage.setItem('access', d.access)
    localStorage.setItem('refresh', d.refresh)
  }

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login/', { email, password })
    saveTokens(data)
    const me = await api.get('/auth/me/')
    setUser(me.data)
    return me.data
  }

  const register = async (payload) => {
    const { data } = await api.post('/auth/register/', payload)
    saveTokens(data)
    setUser(data.user)
    return data.user
  }

  const logout = () => {
    localStorage.clear()
    setUser(null)
  }

  return <AuthCtx.Provider value={{ user, loading, login, register, logout, setUser }}>{children}</AuthCtx.Provider>
}
