import { DIAS_CORTOS, hhmm } from '../util'

const INICIO = 7 * 60
const FIN = 23 * 60

/** Grilla Lunes–Sábado de 7 a 23 hs con las materias pintadas (como la planilla). */
export default function GrillaSemanal({ materias, colores }) {
  const horas = []
  for (let m = INICIO; m < FIN; m += 60) horas.push(m)
  const total = FIN - INICIO
  const usaDomingo = materias.some((m) => m.bloques.some((b) => b.dia === 7))
  const dias = usaDomingo ? [1, 2, 3, 4, 5, 6, 7] : [1, 2, 3, 4, 5, 6]

  return (
    <div className="grilla" style={{ '--dias': dias.length }}>
      <div className="grilla-esquina" />
      {dias.map((d) => (
        <div key={d} className="grilla-dia">{DIAS_CORTOS[d]}</div>
      ))}
      <div className="grilla-horas">
        {horas.map((h) => (
          <span key={h} style={{ top: `${((h - INICIO) / total) * 100}%` }}>{hhmm(h)}</span>
        ))}
      </div>
      {dias.map((d) => (
        <div key={d} className="grilla-col">
          {horas.map((h) => (
            <span key={h} className="grilla-linea" style={{ top: `${((h - INICIO) / total) * 100}%` }} />
          ))}
          {materias.flatMap((m) =>
            m.bloques
              .filter((b) => b.dia === d)
              .map((b, i) => {
                const c = colores[m.plan_id] || { fondo: '#64748B', texto: '#fff' }
                const desde = Math.max(b.desde, INICIO)
                const hasta = Math.min(b.hasta, FIN)
                return (
                  <div
                    key={`${m.plan_id}-${i}`}
                    className="bloque"
                    style={{
                      top: `${((desde - INICIO) / total) * 100}%`,
                      height: `${((hasta - desde) / total) * 100}%`,
                      background: c.fondo,
                      color: c.texto,
                    }}
                    title={`${m.materia} (${m.comision}) ${b.rango}${b.aula ? `, ${b.aula}` : ''}`}
                  >
                    <strong>{m.materia}</strong>
                    <span>
                      {b.rango}
                      {b.aula && b.aula !== 'NO ASIGNADO' ? `, ${b.aula}` : ''}
                    </span>
                  </div>
                )
              }),
          )}
        </div>
      ))}
    </div>
  )
}
