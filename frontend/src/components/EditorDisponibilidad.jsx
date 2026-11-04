import { DIAS } from '../util'

const HORAS = Array.from({ length: 17 }, (_, i) => 7 + i) // 7..23

export const PRESETS = {
  libre: { nombre: 'Cualquier horario', franjas: null },
  trabajo: {
    nombre: 'Trabajo de día',
    franjas: [1, 2, 3, 4, 5].map((dia) => ({ dia, desde: '18:00', hasta: '23:00' })).concat([{ dia: 6, desde: '08:00', hasta: '14:00' }]),
  },
  manana: {
    nombre: 'Sólo mañana',
    franjas: [1, 2, 3, 4, 5, 6].map((dia) => ({ dia, desde: '07:00', hasta: '13:00' })),
  },
  tarde: {
    nombre: 'Sólo tarde',
    franjas: [1, 2, 3, 4, 5].map((dia) => ({ dia, desde: '13:00', hasta: '18:00' })),
  },
}

const hora = (txt) => Number(txt.split(':')[0])
const txt = (h) => `${String(h).padStart(2, '0')}:00`

/** franjas = null (sin restricción) o [{dia, desde:'HH:MM', hasta:'HH:MM'}] (una por día) */
export default function EditorDisponibilidad({ franjas, onChange }) {
  const porDia = Object.fromEntries((franjas || []).map((f) => [f.dia, f]))
  const presetActual = Object.entries(PRESETS).find(
    ([, p]) => JSON.stringify(p.franjas) === JSON.stringify(franjas),
  )?.[0]

  const actualizarDia = (dia, cambios) => {
    const base = franjas || [1, 2, 3, 4, 5, 6].map((d) => ({ dia: d, desde: '07:00', hasta: '23:00' }))
    const existe = base.some((f) => f.dia === dia)
    let nuevas
    if (cambios === null) nuevas = base.filter((f) => f.dia !== dia)
    else if (existe) nuevas = base.map((f) => (f.dia === dia ? { ...f, ...cambios } : f))
    else nuevas = [...base, { dia, desde: '18:00', hasta: '23:00', ...cambios }]
    onChange(nuevas.sort((a, b) => a.dia - b.dia))
  }

  return (
    <fieldset className="disponibilidad">
      <legend>¿Cuándo podés cursar?</legend>
      <div className="presets">
        {Object.entries(PRESETS).map(([clave, p]) => (
          <button
            type="button"
            key={clave}
            className={presetActual === clave ? 'chip activo' : 'chip'}
            aria-pressed={presetActual === clave}
            onClick={() => onChange(p.franjas)}
          >
            {p.nombre}
          </button>
        ))}
      </div>
      {franjas && (
        <table className="tabla-dias">
          <tbody>
            {[1, 2, 3, 4, 5, 6].map((d) => {
              const f = porDia[d]
              return (
                <tr key={d} className={f ? '' : 'apagado'}>
                  <td>
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={!!f}
                        onChange={(e) => actualizarDia(d, e.target.checked ? {} : null)}
                      />
                      {DIAS[d]}
                    </label>
                  </td>
                  <td>
                    <select
                      disabled={!f}
                      value={f ? hora(f.desde) : 18}
                      aria-label={`${DIAS[d]} desde`}
                      onChange={(e) => actualizarDia(d, { desde: txt(e.target.value) })}
                    >
                      {HORAS.slice(0, -1).map((h) => <option key={h} value={h}>{h} hs</option>)}
                    </select>
                  </td>
                  <td>a</td>
                  <td>
                    <select
                      disabled={!f}
                      value={f ? hora(f.hasta) : 23}
                      aria-label={`${DIAS[d]} hasta`}
                      onChange={(e) => actualizarDia(d, { hasta: txt(e.target.value) })}
                    >
                      {HORAS.slice(1).map((h) => <option key={h} value={h}>{h} hs</option>)}
                    </select>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </fieldset>
  )
}
