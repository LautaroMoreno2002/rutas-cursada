"""Parseo de días y horarios del PDF + utilidades de franjas horarias."""
import re

from .texto import sin_acentos

DIAS = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado", 7: "Domingo"}
DIAS_CORTOS = {1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie", 6: "Sáb", 7: "Dom"}
_PREFIJOS = [("lu", 1), ("ma", 2), ("mi", 3), ("ju", 4), ("vi", 5), ("sa", 6), ("do", 7)]

TURNOS = {
    "manana": (7 * 60, 13 * 60),
    "tarde": (13 * 60, 18 * 60),
    "noche": (18 * 60, 23 * 60),
}

_RE_HORARIO = re.compile(
    r"(\d{1,2})(?:[:.h](\d{2}))?\s*(?:hs?\.?)?\s*(?:a|-|–|al|hasta)\s*(\d{1,2})(?:[:.h](\d{2}))?"
)


def parsear_dia(texto: str | None) -> int | None:
    if not texto:
        return None
    t = sin_acentos(texto).strip().lower()
    for prefijo, numero in _PREFIJOS:
        if t.startswith(prefijo):
            return numero
    return None


def parsear_horario(texto: str | None) -> tuple[int, int] | tuple[None, None]:
    """'18:00 a 22:00' / '18 a 22' / '8.30-12.30 hs' -> (minuto_desde, minuto_hasta)."""
    if not texto:
        return None, None
    m = _RE_HORARIO.search(str(texto).lower())
    if not m:
        return None, None
    h1, m1, h2, m2 = m.groups()
    desde = int(h1) * 60 + int(m1 or 0)
    hasta = int(h2) * 60 + int(m2 or 0)
    if hasta <= desde or hasta > 24 * 60:
        return None, None
    return desde, hasta


def fmt_hora(minutos: int | None) -> str:
    if minutos is None:
        return ""
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def fmt_rango(desde, hasta) -> str:
    if desde is None or hasta is None:
        return ""
    corto = lambda m: f"{m // 60}" if m % 60 == 0 else f"{m // 60}:{m % 60:02d}"  # noqa: E731
    return f"{corto(desde)} a {corto(hasta)}"


def se_superponen(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    """Bloques (dia, desde, hasta)."""
    return a[0] == b[0] and a[1] < b[2] and b[1] < a[2]


def turno_de(desde: int, hasta: int) -> str:
    """Turno con mayor solapamiento."""
    mejor, solape_max = "noche", -1
    for nombre, (t0, t1) in TURNOS.items():
        solape = max(0, min(hasta, t1) - max(desde, t0))
        if solape > solape_max:
            mejor, solape_max = nombre, solape
    return mejor
