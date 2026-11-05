import { useMemo, useRef, useState } from 'react'
import { api, descargar } from '../api'
import { useSesion } from '../sesion'
import EditorDisponibilidad, { PRESETS } from '../components/EditorDisponibilidad'
import GrillaSemanal from '../components/GrillaSemanal'
import LineaRuta from '../components/LineaRuta'
import { mapaColores, plural } from '../util'

const COLORES_LINEA = ['#2F4BD8', '#16A34A', '#E5322D', '#7C3AED', '#D97706', '#0891B2', '#DB2777', '#475569']

function proximosSemestres() {
  const hoy = new Date()
  let anio = hoy.getFullYear()
  let sem = hoy.getMonth() + 1 <= 2 ? 1 : hoy.getMonth() + 1 <= 7 ? 2 : 1
  if (hoy.getMonth() + 1 > 7) anio += 1
  const res = []
  for (let i = 0; i < 4; i++) {
    res.push({ anio, semestre: sem })
    if (sem === 1) sem = 2
    else {
      sem = 1
      anio += 1
    }
  }
  return res
}

const DEFAULTS = {
  inicio: '',
  max_materias: 4,
  max_horas: '',
  turno_preferido: '',
  disponibilidad: PRESETS.trabajo.franjas,
  objetivo_anios: '',
  cantidad_rutas: 4,
  asumir_cursando_aprobadas: true,
  incluir_sin_oferta: true,
}

function desdePreferencias(p) {
  if (!p) return DEFAULTS
  return {
    ...DEFAULTS,
    inicio: p.anio_inicio && p.semestre_inicio ? `${p.anio_inicio}-${p.semestre_inicio}` : '',
    max_materias: p.max_materias ?? DEFAULTS.max_materias,
    max_horas: p.max_horas ?? '',
    turno_preferido: p.turno_preferido ?? '',
    disponibilidad: p.disponibilidad === undefined ? DEFAULTS.disponibilidad : p.disponibilidad,
    objetivo_anios: p.objetivo_anios ?? '',
    cantidad_rutas: p.cantidad_rutas ?? DEFAULTS.cantidad_rutas,
    asumir_cursando_aprobadas: p.asumir_cursando_aprobadas ?? true,
    incluir_sin_oferta: p.incluir_sin_oferta ?? true,
  }
}

function aBody(f) {
  const [anio, sem] = f.inicio ? f.inicio.split('-').map(Number) : [null, null]
  return {
    anio_inicio: anio,
    semestre_inicio: sem,
    max_materias: Number(f.max_materias),
    max_horas: f.max_horas === '' ? null : Number(f.max_horas),
    turno_preferido: f.turno_preferido || null,
    disponibilidad: f.disponibilidad,
    trabaja: JSON.stringify(f.disponibilidad) === JSON.stringify(PRESETS.trabajo.franjas),
    objetivo_anios: f.objetivo_anios === '' ? null : Number(f.objetivo_anios),
    cantidad_rutas: Number(f.cantidad_rutas),
    asumir_cursando_aprobadas: f.asumir_cursando_aprobadas,
    incluir_sin_oferta: f.incluir_sin_oferta,
  }
}

function Semestre({ sem, colores }) {
  const [verPendientes, setVerPendientes] = useState(false)
  const otras = sem.candidatas.filter((c) => !c.cursar)
  return (
    <section className="semestre">
      <header className="semestre-cabecera">
        <h3>{sem.titulo.replace('SEMESTRE', 'semestre')}</h3>
        <span className="semestre-meta">
          {sem.materias.length ? `${plural(sem.materias.length, 'materia', 'materias')}, ${sem.horas} hs por semana` : 'Sin materias'}
          {sem.oferta_estimada && <em className="estimada" title="Todavía no está publicada la oferta de ese semestre">Horarios {sem.fuente_oferta}</em>}
        </span>
      </header>
      {sem.materias.length === 0 ? (
        <p className="nota">Lo que te falta no se dicta este semestre o no encaja con tus horarios.</p>
      ) : (
        <div className="semestre-cuerpo">
          <div className="grilla-scroll">
            <GrillaSemanal materias={sem.materias} colores={colores} />
          </div>
          <ul className="lista-cursar">
            {sem.materias.map((m) => (
              <li key={m.plan_id} style={{ '--color': colores[m.plan_id]?.fondo }}>
                <strong>{m.materia}</strong>
                <span>
                  {m.continua_anual ? 'Continúa (anual), ' : m.anual ? 'Anual, ' : ''}
                  {m.horario_a_confirmar && !m.bloques.length ? 'horario a confirmar' : m.comision}
                  {m.docentes?.length ? `, ${m.docentes.join(' y ')}` : ''}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {otras.length > 0 && (
        <div className="pendientes">
          <button className="btn-texto" aria-expanded={verPendientes} onClick={() => setVerPendientes(!verPendientes)}>
            {verPendientes ? 'Ocultar' : 'Ver'} las otras {plural(otras.length, 'materia pendiente', 'materias pendientes')}
          </button>
          {verPendientes && (
            <table className="tabla-pendientes">
              <thead>
                <tr><th>Materia</th><th>Disponible</th><th>Días y horarios</th><th>Por qué no</th></tr>
              </thead>
              <tbody>
                {otras.map((c) => (
                  <tr key={c.plan_id} className={c.disponible ? 'disp' : 'no-disp'}>
                    <td>{c.materia}</td>
                    <td>{c.disponible ? 'Sí' : 'No'}</td>
                    <td>{[c.dias, c.horarios].filter(Boolean).join(', ') || '-'}</td>
                    <td>{c.correlativas_faltantes.length ? `Falta ${c.correlativas_faltantes.join(', ')}` : c.motivo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  )
}

export default function Planificar() {
  const { alumno } = useSesion()
  const [f, setF] = useState(() => desdePreferencias(alumno.preferencias))
  const [resultado, setResultado] = useState(null)
  const [elegida, setElegida] = useState(0)
  const [cargando, setCargando] = useState(false)
  const [bajando, setBajando] = useState(false)
  const [error, setError] = useState('')
  const opcionesInicio = useMemo(proximosSemestres, [])
  const refResultados = useRef(null)

  const set = (campo) => (e) => setF({ ...f, [campo]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const calcular = async (e) => {
    e?.preventDefault()
    setCargando(true)
    setError('')
    try {
      const r = await api('/rutas', { method: 'POST', body: aBody(f) })
      setResultado(r)
      setElegida(0)
      if (window.matchMedia('(max-width: 980px)').matches) {
        requestAnimationFrame(() => refResultados.current?.scrollIntoView({ block: 'start' }))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  const bajarExcel = async () => {
    setBajando(true)
    try {
      descargar(await api('/rutas/excel', { method: 'POST', body: aBody(f), archivo: true }), 'rutas_de_cursada.xlsx')
    } catch (err) {
      setError(err.message)
    } finally {
      setBajando(false)
    }
  }

  const ruta = resultado?.rutas[elegida]
  const colores = useMemo(
    () => mapaColores((resultado?.rutas || []).flatMap((r) => r.semestres.flatMap((s) => s.materias.map((m) => m.plan_id)))),
    [resultado],
  )

  return (
    <div className="planificar">
      <form className="panel form-parametros" onSubmit={calcular}>
        <h1>Planificá tu cursada</h1>

        <label>
          Empezar en
          <select value={f.inicio} onChange={set('inicio')}>
            <option value="">El próximo semestre</option>
            {opcionesInicio.map((o) => (
              <option key={`${o.anio}-${o.semestre}`} value={`${o.anio}-${o.semestre}`}>
                {o.semestre}° semestre {o.anio}
              </option>
            ))}
          </select>
        </label>

        <div className="dos-col">
          <label>
            Materias por semestre
            <input type="number" min="1" max="10" value={f.max_materias} onChange={set('max_materias')} required />
          </label>
          <label>
            Máx. horas semanales
            <input type="number" min="1" max="80" placeholder="Sin límite" value={f.max_horas} onChange={set('max_horas')} />
          </label>
        </div>

        <EditorDisponibilidad franjas={f.disponibilidad} onChange={(d) => setF({ ...f, disponibilidad: d })} />

        <label>
          Turno preferido
          <select value={f.turno_preferido} onChange={set('turno_preferido')}>
            <option value="">Me da igual</option>
            <option value="manana">Mañana</option>
            <option value="tarde">Tarde</option>
            <option value="noche">Noche</option>
          </select>
        </label>

        <div className="dos-col">
          <label>
            Quiero terminar en
            <span className="con-unidad">
              <input type="number" min="0.5" max="15" step="0.5" placeholder="-" value={f.objetivo_anios} onChange={set('objetivo_anios')} />
              años
            </span>
          </label>
          <label>
            Rutas a mostrar
            <input type="number" min="1" max="8" value={f.cantidad_rutas} onChange={set('cantidad_rutas')} />
          </label>
        </div>

        <label className="check">
          <input type="checkbox" checked={f.asumir_cursando_aprobadas} onChange={set('asumir_cursando_aprobadas')} />
          Contar como aprobadas las que estoy cursando
        </label>
        <label className="check">
          <input type="checkbox" checked={f.incluir_sin_oferta} onChange={set('incluir_sin_oferta')} />
          Incluir materias sin horarios publicados
        </label>

        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn" disabled={cargando}>{cargando ? 'Calculando…' : 'Calcular rutas'}</button>
      </form>

      <div className="resultados" aria-live="polite" ref={refResultados}>
        {!resultado && !cargando && (
          <div className="vacio">
            <p>Elegí tus días y horarios y cuántas materias querés cursar por semestre. Vas a ver acá cada ruta posible para recibirte, semestre por semestre.</p>
            <p className="nota">Para los semestres cuya oferta todavía no se publicó se usan los horarios del mismo semestre del año anterior.</p>
          </div>
        )}
        {resultado && (
          <>
            <div className="resumen">
              <p>
                Te {resultado.pendientes === 1 ? 'falta' : 'faltan'} <strong>{plural(resultado.pendientes, 'materia', 'materias')}</strong>.
                {resultado.minimo_teorico_semestres > 0 &&
                  ` Por correlativas, no podrías terminar en menos de ${plural(resultado.minimo_teorico_semestres, 'semestre', 'semestres')}.`}
              </p>
              <button className="btn btn-secundario" onClick={bajarExcel} disabled={bajando}>
                {bajando ? 'Generando…' : 'Descargar Excel'}
              </button>
            </div>

            {resultado.pendientes === 0 ? (
              <p className="vacio">¡No te queda ninguna materia pendiente!</p>
            ) : (
              <ol className="rutas" aria-label="Rutas posibles">
                {resultado.rutas.map((r, i) => (
                  <li key={r.nombre}>
                    <button
                      className={i === elegida ? 'ruta activa' : 'ruta'}
                      aria-pressed={i === elegida}
                      onClick={() => setElegida(i)}
                      style={{ '--linea': COLORES_LINEA[i % COLORES_LINEA.length] }}
                    >
                      <span className="ruta-titulo">
                        <strong>{r.nombre.replace(/^Ruta \d+ - /, '')}</strong>
                        <span>
                          {r.completa ? `Terminás el ${r.finaliza?.toLowerCase()}` : 'No llega a completar la carrera'}
                          {r.cumple_objetivo === false && ', después de tu objetivo'}
                        </span>
                      </span>
                      <span className="ruta-linea">
                        <LineaRuta ruta={r} color={COLORES_LINEA[i % COLORES_LINEA.length]} />
                      </span>
                      <span className="ruta-total">{r.cantidad_semestres}<small>sem.</small></span>
                    </button>
                  </li>
                ))}
              </ol>
            )}

            {ruta && (
              <article className="detalle-ruta">
                <p className="descripcion">{ruta.descripcion}</p>
                {ruta.sin_planificar.length > 0 && (
                  <div className="alerta">
                    <strong>Materias que no se pudieron ubicar</strong>
                    <ul>
                      {ruta.sin_planificar.map((m) => <li key={m.plan_id}>{m.materia}: {m.motivo}</li>)}
                    </ul>
                  </div>
                )}
                {ruta.semestres.map((s) => (
                  <Semestre key={`${s.anio}-${s.semestre}`} sem={s} colores={colores} />
                ))}
              </article>
            )}
          </>
        )}
      </div>
    </div>
  )
}
