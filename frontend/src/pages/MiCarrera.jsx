import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useSesion } from '../sesion'
import { DIAS_CORTOS, plural } from '../util'

const ESTADOS = [
  ['pendiente', 'Pendiente'],
  ['cursando', 'Cursando'],
  ['aprobada', 'Aprobada'],
]

function textoComision(c) {
  const horarios = c.horarios.map((h) => `${DIAS_CORTOS[h.dia] || '?'} ${h.rango}`).join(', ')
  return `${c.nombre}: ${horarios || 'horario a confirmar'}`
}

export default function MiCarrera() {
  const { alumno } = useSesion()
  const [carrera, setCarrera] = useState(null)
  const [estados, setEstados] = useState({}) // plan_id -> {estado, comision_id}
  const [original, setOriginal] = useState({})
  const [oferta, setOferta] = useState(null)
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    Promise.all([
      api(`/carreras/${alumno.carrera_id}`),
      api('/me/materias'),
      api(`/carreras/${alumno.carrera_id}/oferta`),
    ])
      .then(([c, mias, of]) => {
        setCarrera(c)
        const mapa = {}
        mias.forEach((m) => (mapa[m.plan_id] = { estado: m.estado, comision_id: m.comision_id }))
        setEstados(mapa)
        setOriginal(mapa)
        setOferta(of)
      })
      .catch((e) => setError(e.message))
  }, [alumno.carrera_id])

  const estadoDe = (id) => estados[id]?.estado || 'pendiente'
  const ofertaPorPlan = useMemo(() => {
    const m = {}
    oferta?.materias.forEach((x) => (m[x.plan_id] = x))
    return m
  }, [oferta])

  const grupos = useMemo(() => {
    if (!carrera) return []
    const g = new Map()
    carrera.plan.forEach((m) => {
      const clave = m.otro_requisito ? 'otros' : m.semestre_sugerido ?? 'sin'
      if (!g.has(clave)) g.set(clave, [])
      g.get(clave).push(m)
    })
    const orden = [...g.keys()].sort((a, b) => {
      const v = (k) => (k === 'otros' ? 1000 : k === 'sin' ? 999 : k)
      return v(a) - v(b)
    })
    return orden.map((k) => ({
      clave: k,
      titulo: k === 'otros' ? 'Otros requisitos académicos' : k === 'sin' ? 'Sin semestre sugerido' : `Semestre ${k}`,
      materias: g.get(k),
    }))
  }, [carrera])

  const cambios = useMemo(() => {
    const ids = new Set([...Object.keys(estados), ...Object.keys(original)])
    return [...ids].filter((id) => {
      const a = estados[id] || { estado: 'pendiente' }
      const b = original[id] || { estado: 'pendiente' }
      return a.estado !== b.estado || (a.comision_id || null) !== (b.comision_id || null)
    })
  }, [estados, original])

  if (error) return <p className="error">{error}</p>
  if (!carrera) return <p className="cargando">Cargando plan de estudios…</p>

  const total = carrera.plan.length
  const aprobadas = carrera.plan.filter((m) => estadoDe(m.plan_id) === 'aprobada').length
  const cursando = carrera.plan.filter((m) => estadoDe(m.plan_id) === 'cursando').length
  const nombre = Object.fromEntries(carrera.plan.map((m) => [m.plan_id, m.nombre]))

  const setEstado = (id, estado) => {
    setAviso('')
    setEstados((prev) => ({ ...prev, [id]: { estado, comision_id: estado === 'cursando' ? prev[id]?.comision_id : null } }))
  }
  const setComision = (id, comision_id) =>
    setEstados((prev) => ({ ...prev, [id]: { ...prev[id], comision_id: comision_id ? Number(comision_id) : null } }))

  const aprobarGrupo = (materias) =>
    setEstados((prev) => {
      const n = { ...prev }
      materias.forEach((m) => (n[m.plan_id] = { estado: 'aprobada', comision_id: null }))
      return n
    })

  const guardar = async () => {
    setGuardando(true)
    setError('')
    try {
      const body = {
        materias: cambios.map((id) => ({
          plan_id: Number(id),
          estado: estados[id]?.estado || 'pendiente',
          comision_id: estados[id]?.comision_id || null,
        })),
      }
      const res = await api('/me/materias', { method: 'PUT', body })
      const mapa = {}
      res.forEach((m) => (mapa[m.plan_id] = { estado: m.estado, comision_id: m.comision_id }))
      setEstados(mapa)
      setOriginal(mapa)
      setAviso('Progreso guardado')
    } catch (e) {
      setError(e.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="mi-carrera">
      <header className="cabecera-pagina">
        <div>
          <h1>{carrera.nombre}</h1>
          <p className="sub">
            {aprobadas} de {total} aprobadas, {plural(cursando, 'materia', 'materias')} en curso.{' '}
            <Link to="/elegir-carrera">Cambiar de carrera</Link>
          </p>
        </div>
        <div className="progreso" aria-label={`${aprobadas} de ${total} materias aprobadas`}>
          <span className="progreso-aprobadas" style={{ width: `${(aprobadas / total) * 100}%` }} />
          <span className="progreso-cursando" style={{ width: `${(cursando / total) * 100}%` }} />
        </div>
      </header>

      {oferta?.periodo && (
        <p className="nota">
          Si estás cursando, elegí tu comisión del {oferta.periodo.nombre}: así tus compañeros ven cuántos están en
          cada una.
        </p>
      )}

      {grupos.map((g) => (
        <section key={g.clave} className="grupo-semestre">
          <div className="grupo-cabecera">
            <h2>{g.titulo}</h2>
            {g.materias.some((m) => estadoDe(m.plan_id) !== 'aprobada') && (
              <button className="btn-texto" onClick={() => aprobarGrupo(g.materias)}>
                Marcar todas como aprobadas
              </button>
            )}
          </div>
          <ul className="filas-materias">
            {g.materias.map((m) => {
              const estado = estadoDe(m.plan_id)
              const faltan = m.correlativas.filter((c) => estadoDe(c) !== 'aprobada')
              const of = ofertaPorPlan[m.plan_id]
              return (
                <li key={m.plan_id} className={`fila-materia estado-${estado}`}>
                  <div className="fila-info">
                    <span className="fila-nombre">{m.nombre}</span>
                    <span className="fila-meta">
                      {[m.horas ? `${m.horas} hs semanales` : null, m.anual ? 'anual' : null].filter(Boolean).join(', ')}
                      {faltan.length > 0 && estado !== 'aprobada' && (
                        <span className="falta"> Necesita {faltan.map((c) => nombre[c]).join(', ')}</span>
                      )}
                    </span>
                  </div>
                  <div className="segmentado" role="radiogroup" aria-label={`Estado de ${m.nombre}`}>
                    {ESTADOS.map(([valor, etiqueta]) => (
                      <button
                        key={valor}
                        role="radio"
                        aria-checked={estado === valor}
                        className={estado === valor ? `activo ${valor}` : ''}
                        onClick={() => setEstado(m.plan_id, valor)}
                      >
                        {etiqueta}
                      </button>
                    ))}
                  </div>
                  {estado === 'cursando' && (
                    <div className="fila-comision">
                      {of ? (
                        <select
                          value={estados[m.plan_id]?.comision_id || ''}
                          onChange={(e) => setComision(m.plan_id, e.target.value)}
                          aria-label={`Comisión de ${m.nombre}`}
                        >
                          <option value="">¿En qué comisión?</option>
                          {of.comisiones.map((c) => (
                            <option key={c.id} value={c.id}>
                              {textoComision(c)} ({plural(c.cursando, 'alumno', 'alumnos')})
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="nota">No figura en la oferta del período actual.</span>
                      )}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      ))}

      <div className={`barra-guardar ${cambios.length || aviso ? 'visible' : ''}`}>
        <span>{aviso || (cambios.length ? plural(cambios.length, 'cambio sin guardar', 'cambios sin guardar') : '')}</span>
        <button className="btn" onClick={guardar} disabled={!cambios.length || guardando}>
          {guardando ? 'Guardando…' : 'Guardar progreso'}
        </button>
      </div>
    </div>
  )
}
