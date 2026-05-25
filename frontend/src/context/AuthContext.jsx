import { createContext, useContext, useState, useCallback } from 'react'
import api from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))

  const login = useCallback(async (password) => {
    const res = await api.post('/auth/login', { password })
    const { token: t } = res.data
    localStorage.setItem('token', t)
    setToken(t)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
