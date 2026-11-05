const BASE = import.meta.env.VITE_API_URL || '/api'

export class ApiError extends Error {
  constructor(status, mensaje) {
    super(mensaje)
    this.status = status
  }
}

function leerToken() {
  try {
    return localStorage.getItem('rutas_token')
  } catch {
    return null
  }
}

export function guardarToken(token) {
  try {
    if (token) localStorage.setItem('rutas_token', token)
    else localStorage.removeItem('rutas_token')
  } catch {
    /* sin almacenamiento: la sesión dura lo que la pestaña */
  }
}

function mensajeDeError(data, status) {
  if (data && typeof data.detail === 'string') return data.detail
  if (data && Array.isArray(data.detail)) {
    return data.detail.map((d) => d.msg.replace('Value error, ', '')).join('. ')
  }
  return `Error ${status} al comunicarse con el servidor`
}

export async function api(ruta, { method = 'GET', body, archivo = false } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = leerToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let resp
  try {
    resp = await fetch(BASE + ruta, { method, headers, body: body ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError(0, 'No se pudo conectar con la API. ¿Está corriendo el backend?')
  }
  if (!resp.ok) {
    let data = null
    try {
      data = await resp.json()
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(resp.status, mensajeDeError(data, resp.status))
  }
  if (archivo) return resp.blob()
  if (resp.status === 204) return null
  return resp.json()
}

export function descargar(blob, nombre) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
