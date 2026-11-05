import { useState } from 'react'
import { useSesion } from '../sesion'
import LineaRuta from '../components/LineaRuta'

// Ruta de ejemplo para la portada: muestra qué devuelve la app antes de registrarse
const EJEMPLO = {
  nombre: 'Así se ve una ruta',
  semestres: [
    { anio: 2027, semestre: 1, materias: [1, 2, 3, 4] },
    { anio: 2027, semestre: 2, materias: [1, 2, 3] },
    { anio: 2028, semestre: 1, materias: [1, 2] },
    { anio: 2028, semestre: 2, materias: [1, 2, 3] },
    { anio: 2029, semestre: 1, materias: [1] },
  ],
}

export default function Ingresar() {
  const { ingresar } = useSesion()
  const [modo, setModo] = useState('login')
  const [datos, setDatos] = useState({ nombre: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const cambiar = (e) => setDatos({ ...datos, [e.target.name]: e.target.value })

  const enviar = async (e) => {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await ingresar(modo, modo === 'registro' ? datos : { email: datos.email, password: datos.password })
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="portada">
      <section className="portada-texto">
        <h1>¿Cuántos semestres te faltan, de verdad?</h1>
        <p>
          Cargá las materias que aprobaste y las que estás cursando. Con la oferta de comisiones de la
          universidad, tus días y horarios libres y cuántas materias querés cursar, armamos los caminos
          posibles para terminar la carrera.
        </p>
        <div className="portada-ejemplo">
          <LineaRuta ruta={EJEMPLO} color="var(--birome)" grande />
          <p className="nota">Cada punto es un semestre; su tamaño, cuántas materias cursás.</p>
        </div>
      </section>

      <form className="panel form-ingreso" onSubmit={enviar}>
        <div className="pestanias" role="tablist">
          <button type="button" role="tab" aria-selected={modo === 'login'} onClick={() => setModo('login')}>
            Ingresar
          </button>
          <button type="button" role="tab" aria-selected={modo === 'registro'} onClick={() => setModo('registro')}>
            Crear cuenta
          </button>
        </div>
        {modo === 'registro' && (
          <label>
            Nombre
            <input name="nombre" value={datos.nombre} onChange={cambiar} required minLength={2} autoComplete="name" />
          </label>
        )}
        <label>
          Email
          <input name="email" type="email" value={datos.email} onChange={cambiar} required autoComplete="email" />
        </label>
        <label>
          Contraseña
          <input
            name="password"
            type="password"
            value={datos.password}
            onChange={cambiar}
            required
            minLength={6}
            autoComplete={modo === 'registro' ? 'new-password' : 'current-password'}
          />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn" disabled={enviando}>
          {enviando ? 'Un momento…' : modo === 'registro' ? 'Crear cuenta' : 'Ingresar'}
        </button>
      </form>
    </main>
  )
}
