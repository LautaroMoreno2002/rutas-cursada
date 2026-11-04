import { Navigate, NavLink, Route, Routes } from 'react-router-dom'
import { useSesion } from './sesion'
import Ingresar from './pages/Ingresar'
import ElegirCarrera from './pages/ElegirCarrera'
import MiCarrera from './pages/MiCarrera'
import Planificar from './pages/Planificar'
import Oferta from './pages/Oferta'
import Logo from './components/Logo'

function Barra() {
  const { alumno, salir } = useSesion()
  return (
    <header className="barra">
      <div className="barra-interior">
        <NavLink to="/" className="marca">
          <Logo />
          <span>Rutas de cursada</span>
        </NavLink>
        {alumno && (
          <>
            <nav className="nav">
              <NavLink to="/carrera">Mi carrera</NavLink>
              <NavLink to="/planificar">Planificar</NavLink>
              <NavLink to="/oferta">Oferta</NavLink>
            </nav>
            <div className="usuario">
              <span className="usuario-nombre">{alumno.nombre}</span>
              <button className="btn-texto" onClick={salir}>Salir</button>
            </div>
          </>
        )}
      </div>
    </header>
  )
}

export default function App() {
  const { alumno, cargando } = useSesion()

  if (cargando) return <div className="cargando-pagina">Cargando…</div>

  if (!alumno) {
    return (
      <>
        <Barra />
        <Ingresar />
      </>
    )
  }

  const inicio = alumno.carrera_id ? '/carrera' : '/elegir-carrera'
  return (
    <>
      <Barra />
      <main className="contenido">
        <Routes>
          <Route path="/elegir-carrera" element={<ElegirCarrera />} />
          <Route path="/carrera" element={alumno.carrera_id ? <MiCarrera /> : <Navigate to="/elegir-carrera" />} />
          <Route path="/planificar" element={alumno.carrera_id ? <Planificar /> : <Navigate to="/elegir-carrera" />} />
          <Route path="/oferta" element={alumno.carrera_id ? <Oferta /> : <Navigate to="/elegir-carrera" />} />
          <Route path="*" element={<Navigate to={inicio} replace />} />
        </Routes>
      </main>
    </>
  )
}
