import { semCorto } from '../util'

/** Una ruta dibujada como línea de subte: una estación por semestre,
 *  más grande cuantas más materias se cursan en ese semestre. */
export default function LineaRuta({ ruta, color = 'var(--birome)', grande = false, seleccionado }) {
  const sems = ruta.semestres
  const paso = grande ? 74 : 56
  const alto = grande ? 78 : 62
  const y = grande ? 30 : 24
  const margen = 20
  const ancho = margen * 2 + Math.max(0, sems.length - 1) * paso
  const radio = (n) => (n ? (grande ? 8 : 7) + (Math.min(n, 6) - 1) * (grande ? 2.2 : 1.6) : 3)

  return (
    <svg
      className="linea-ruta"
      viewBox={`0 0 ${ancho} ${alto}`}
      width={ancho}
      height={alto}
      role="img"
      aria-label={`${ruta.nombre}: ${sems.length} semestres`}
    >
      <line x1={margen} y1={y} x2={ancho - margen} y2={y} stroke={color} strokeWidth={grande ? 7 : 5} strokeLinecap="round" />
      {sems.map((s, i) => {
        const n = s.materias.length
        const x = margen + i * paso
        return (
          <g key={`${s.anio}-${s.semestre}`}>
            <circle
              cx={x}
              cy={y}
              r={radio(n)}
              fill={n ? 'var(--superficie)' : color}
              stroke={n ? (seleccionado === i ? 'var(--tinta)' : color) : 'none'}
              strokeWidth={grande ? 3.5 : 3}
            />
            {n > 0 && (
              <text x={x} y={y + 4} textAnchor="middle" className="linea-num" fill="var(--tinta)">
                {n}
              </text>
            )}
            <text x={x} y={alto - 6} textAnchor="middle" className="linea-sem">
              {semCorto(s.anio, s.semestre)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
