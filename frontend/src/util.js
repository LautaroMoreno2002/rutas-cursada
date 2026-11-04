// Colores fuertes por materia (como en la planilla), con color de texto legible
const PALETA = [
  ['#E5322D', '#fff'], ['#16A34A', '#fff'], ['#F59E0B', '#1B2236'], ['#1B2236', '#fff'],
  ['#D946EF', '#fff'], ['#06B6D4', '#1B2236'], ['#2563EB', '#fff'], ['#FACC15', '#1B2236'],
  ['#7C3AED', '#fff'], ['#C2410C', '#fff'], ['#84CC16', '#1B2236'], ['#64748B', '#fff'],
]

export function colorMateria(planId, orden) {
  const i = orden ?? planId
  const [fondo, texto] = PALETA[((i % PALETA.length) + PALETA.length) % PALETA.length]
  return { fondo, texto }
}

// Asigna colores distintos a las materias en el orden en que aparecen
export function mapaColores(ids) {
  const mapa = {}
  ids.forEach((id, i) => {
    if (!(id in mapa)) mapa[id] = colorMateria(id, Object.keys(mapa).length)
  })
  return mapa
}

export const DIAS = ['', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
export const DIAS_CORTOS = ['', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

export const hhmm = (min) => `${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`

export const semCorto = (anio, semestre) => `${semestre}°${String(anio).slice(2)}`

export function plural(n, uno, varios) {
  return `${n} ${n === 1 ? uno : varios}`
}
