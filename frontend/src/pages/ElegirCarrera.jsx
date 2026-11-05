import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useSesion } from '../sesion'

export default function ElegirCarrera() {
  const { alumno, actualizar } = useSesion()
  const [carreras, setCarreras] = useState(null)
  const [filtro, setFiltro] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api('/carreras').then(setCarreras).catch((e) => setError(e.message))
  }, [])

  const elegir = async (c) => {
    if (alumno.carrera_id && alumno.carrera_id !== c.id &&
        !window.confirm('Al cambiar de carrera se borra el progreso cargado. ¿Continuar?')) return
    try {
      await actualizar({ carrera_id: c.id })
      navigate('/carrera')
    } catch (e) {
      setError(e.message)
    }
  }

  const visibles = (carreras || []).filter((c) => c.nombre.toLowerCase().includes(filtro.toLowerCase()))

  return (
    <div className="angosto">
      <h1>¿Qué carrera estudiás?</h1>
      {error && <p className="error">{error}</p>}
      {carreras && carreras.length === 0 && (
        <p className="vacio">
          Todavía no hay carreras cargadas. Corré el scraper e importalas desde la API de administración
          (o cargá los datos de demostración con <code>python -m app.cli demo</code>).
        </p>
      )}
      {carreras && carreras.length > 6 && (
        <input className="buscador" placeholder="Buscar carrera" value={filtro} onChange={(e) => setFiltro(e.target.value)} />
      )}
      <ul className="lista-carreras">
        {visibles.map((c) => (
          <li key={c.id}>
            <button onClick={() => elegir(c)} className={c.id === alumno.carrera_id ? 'actual' : ''}>
              <strong>{c.nombre}</strong>
              <span>
                {[c.titulo_oficial, c.duracion, `${c.cantidad_materias} materias`].filter(Boolean).join(', ')}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
