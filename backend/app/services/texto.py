"""Normalización y emparejamiento de nombres de materias.

El plan de estudios (HTML) y el PDF de oferta escriben los nombres distinto
("Bases de Datos II" vs "BASES DE DATOS II", "Programación 2", "Intro. a la ..."),
y las correlativas son texto libre. Este módulo resuelve esas diferencias.
"""
import difflib
import re
import unicodedata

_ROMANOS = {"1": "i", "2": "ii", "3": "iii", "4": "iv", "5": "v", "6": "vi"}
_RE_ROMANO = re.compile(r"^(i{1,3}|iv|v|vi)$")
_ABREVIATURAS = {
    r"\bintrod?\.?\b": "introduccion",
    r"\bprog\.?\b": "programacion",
    r"\bmat\.?\b": "matematica",
    r"\bsist\.?\b": "sistemas",
    r"\bing\.?\b": "ingenieria",
    r"\bbd\b": "bases de datos",
}
_STOP = {"de", "del", "la", "las", "el", "los", "a", "y", "e", "en", "al"}


def sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar(nombre: str | None) -> str:
    if not nombre:
        return ""
    t = sin_acentos(str(nombre)).lower()
    t = re.sub(r"\(.*?\)", " ", t)  # quita códigos "(A0075)"
    for patron, reemplazo in _ABREVIATURAS.items():
        t = re.sub(patron, reemplazo, t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    palabras = [_ROMANOS.get(p, p) for p in t.split()]
    return " ".join(palabras)


def _nivel(normalizado: str) -> str:
    """Numeral final ('ii' en 'programacion ii'), para no confundir I con II."""
    partes = normalizado.split()
    return partes[-1] if partes and _RE_ROMANO.match(partes[-1]) else ""


def _sin_stopwords(normalizado: str) -> str:
    return " ".join(p for p in normalizado.split() if p not in _STOP)


class IndiceNombres:
    """Busca el id que corresponde a un nombre de materia, tolerando diferencias menores."""

    def __init__(self, pares: dict[str, int] | None = None, umbral: float = 0.86):
        self.umbral = umbral
        self._exactos: dict[str, int] = {}
        self._compactos: dict[str, int] = {}
        for nombre, valor in (pares or {}).items():
            self.agregar(nombre, valor)

    def agregar(self, nombre: str, valor: int):
        n = normalizar(nombre)
        if n:
            self._exactos.setdefault(n, valor)
            self._compactos.setdefault(_sin_stopwords(n), valor)

    def buscar(self, nombre: str) -> int | None:
        n = normalizar(nombre)
        if not n:
            return None
        if n in self._exactos:
            return self._exactos[n]
        c = _sin_stopwords(n)
        if c in self._compactos:
            return self._compactos[c]
        nivel = _nivel(n)
        candidatos = [k for k in self._exactos if _nivel(k) == nivel]
        match = difflib.get_close_matches(n, candidatos, n=1, cutoff=self.umbral)
        if match:
            return self._exactos[match[0]]
        # Abreviado al principio: "taller de tesina" vs "taller de tesina de licenciatura"
        prefijos = [k for k in candidatos if len(n) >= 12 and (k.startswith(n) or n.startswith(k))]
        if len(prefijos) == 1:
            return self._exactos[prefijos[0]]
        return None
