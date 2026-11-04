import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, guardarToken } from './api'

const SesionCtx = createContext(null)

export function SesionProvider({ children }) {
  const [alumno, setAlumno] = useState(null)
  const [cargando, setCargando] = useState(true)

  const refrescar = useCallback(async () => {
    try {
      setAlumno(await api('/me'))
    } catch {
      guardarToken(null)
      setAlumno(null)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    refrescar()
  }, [refrescar])

  const ingresar = async (modo, datos) => {
    const r = await api(modo === 'registro' ? '/auth/registro' : '/auth/login', { method: 'POST', body: datos })
    guardarToken(r.token)
    setAlumno(r.alumno)
    return r.alumno
  }

  const salir = () => {
    guardarToken(null)
    setAlumno(null)
  }

  const actualizar = async (cambios) => {
    const a = await api('/me', { method: 'PUT', body: cambios })
    setAlumno(a)
    return a
  }

  return (
    <SesionCtx.Provider value={{ alumno, cargando, ingresar, salir, actualizar, refrescar }}>
      {children}
    </SesionCtx.Provider>
  )
}

export const useSesion = () => useContext(SesionCtx)
