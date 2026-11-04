import { useEffect, useState } from 'react'
import { api } from '../api'
import { useSesion } from '../sesion'
import { DIAS, plural } from '../util'

const TURNOS = { manana: 'mañana', tarde: 'tarde', noche: 'noche' }

export default function Oferta() {
  const { alumno } = useSesion()
  const [periodos, setPeriodos] = useState(null)
  const [periodoId, setPeriodoId] = useState('')
  const [oferta, setOferta] = useState(null)
  const [filtro, setFiltro] = useState('')
  const [turno, setTurno] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api('/periodos')
      .then((r) => {
        setPeriodos(r.periodos)
        setPeriodoId(r.actual_id || '')
      })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!periodoId) return
    setOferta(null)
    api(`/carreras/${alumno.carrera_id}/oferta?periodo_id=${periodoId}`).then(setOferta).catch((e) => setError(e.message))
  }, [periodoId, alumno.carrera_id])

  const coincide = (m) => m.materia.toLowerCase().includes(filtro.toLowerCase())
  const comisionesVisibles = (m) => m.comisiones.filter((c) => !turno || c.horarios.some((h) => h.turno === turno))
  const materias = (oferta?.materias || []).filter((m) => coincide(m) && comisionesVisibles(m).length)

  return (
    <div className="oferta">
      <header className="cabecera-pagina">
        <h1>Oferta de comisiones</h1>
        <div className="filtros">
          <select value={periodoId} onChange={(e) => setPeriodoId(e.target.value)} aria-label="Período">
            {(periodos || []).map((p) => (
              <option key={p.id} value={p.id}>{p.nombre}</option>
            ))}
          </select>
          <select value={turno} onChange={(e) => setTurno(e.target.value)} aria-label="Turno">
            <option value="">Todos los turnos</option>
            {Object.entries(TURNOS).map(([k, v]) => <option key={k} value={k}>Turno {v}</option>)}
          </select>
          <input placeholder="Buscar materia" value={filtro} onChange={(e) => setFiltro(e.target.value)} />
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      {periodos && periodos.length === 0 && <p className="vacio">Todavía no se cargó ninguna oferta de comisiones.</p>}
      {oferta?.periodo && !oferta.periodo.definido && (
        <p className="nota">
          La oferta del {oferta.periodo.nombre} todavía es preliminar: no tiene aulas ni docentes asignados.
        </p>
      )}
      {oferta && materias.length === 0 && <p className="vacio">Ninguna materia de tu carrera coincide con el filtro.</p>}
      <div className="oferta-lista">
        {materias.map((m) => (
          <section key={m.plan_id} className="oferta-materia">
            <h2>
              {m.materia}
              {m.codigo && <span className="codigo">{m.codigo}</span>}
            </h2>
            <table>
              <tbody>
                {comisionesVisibles(m).map((c) => (
                  <tr key={c.id}>
                    <th scope="row">{c.nombre}</th>
                    <td>
                      {c.horarios.map((h, i) => (
                        <div key={i} className="horario">
                          <span className="horario-dia">{DIAS[h.dia] || 'A confirmar'}</span>
                          <span className="horario-rango">{h.rango}</span>
                          {h.aula && h.aula !== 'NO ASIGNADO' && <span className="horario-aula">{h.aula}{h.edificacion ? `, ${h.edificacion}` : ''}</span>}
                        </div>
                      ))}
                    </td>
                    <td className="docentes">{c.docentes.join(', ')}</td>
                    <td className="cursando">{c.cursando ? plural(c.cursando, 'cursando', 'cursando') : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))}
      </div>
    </div>
  )
}
