"""Exporta las rutas a Excel con el mismo formato que la planilla de ejemplo:

* Una hoja por ruta alternativa (+ una hoja "Resumen").
* Por cada semestre: título, grilla Hora x Lunes..Sábado (7 a 23 hs) con las
  materias pintadas, y a la derecha el panel Cursar | Disp | Materias | Días |
  Horarios | HS | Correlativas con todas las materias pendientes de ese momento.
"""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from .horarios import fmt_hora

HORA_INICIO, HORA_FIN = 7, 23
DIAS_GRILLA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
PANEL = ["Cursar", "Disp", "Materias", "Dias", "Horarios", "HS", "Correlativas"]
ANCHOS = {"A": 13.3, "B": 25, "C": 23, "D": 25, "E": 23.5, "F": 21, "G": 24.7, "H": 4,
          "I": 8, "J": 6, "K": 36, "L": 22, "M": 20, "N": 6, "O": 48, "P": 34}

# (relleno, color de letra) — colores fuertes como en la planilla original
PALETA = [
    ("FF0000", "FFFFFF"), ("00B050", "FFFFFF"), ("FF9900", "000000"), ("000000", "FFFFFF"),
    ("FF00FF", "FFFFFF"), ("00FFFF", "000000"), ("0070C0", "FFFFFF"), ("FFFF00", "000000"),
    ("7030A0", "FFFFFF"), ("C65911", "FFFFFF"), ("00FF00", "000000"), ("808080", "FFFFFF"),
]
F_HORA = PatternFill("solid", fgColor="953734")
F_DIA = PatternFill("solid", fgColor="4F81BD")
F_PANEL = PatternFill("solid", fgColor="FF0000")
F_NO_DISP = PatternFill("solid", fgColor="9900FF")
F_DISP = PatternFill("solid", fgColor="93C47D")
BLANCO = Font(color="FFFFFF", bold=True)
FINO = Side(style="thin", color="BFBFBF")
BORDE = Border(left=FINO, right=FINO, top=FINO, bottom=FINO)
CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)
IZQ = Alignment(vertical="center", wrap_text=True)


def _nombre_hoja(nombre: str, usados: set[str]) -> str:
    limpio = "".join(c for c in nombre if c not in '[]:*?/\\')[:31].strip()
    base, i = limpio, 2
    while limpio in usados:
        sufijo = f" ({i})"
        limpio = base[: 31 - len(sufijo)] + sufijo
        i += 1
    usados.add(limpio)
    return limpio


def _colores(rutas: list[dict]) -> dict[int, tuple[PatternFill, Font]]:
    """Un color fijo por materia, igual en todas las hojas."""
    ids = []
    for r in rutas:
        for s in r["semestres"]:
            for m in s["materias"]:
                if m["plan_id"] not in ids:
                    ids.append(m["plan_id"])
    return {
        pid: (PatternFill("solid", fgColor=PALETA[i % len(PALETA)][0]),
              Font(color=PALETA[i % len(PALETA)][1], bold=True))
        for i, pid in enumerate(ids)
    }


def _bloque_semestre(ws, fila: int, sem: dict, colores) -> int:
    """Escribe un semestre a partir de `fila`. Devuelve la próxima fila libre."""
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=7)
    t = ws.cell(fila, 1, sem["titulo"])
    t.font, t.alignment = Font(bold=True, size=13), CENTRO
    if sem.get("oferta_estimada"):
        n = ws.cell(fila, 9, f"Horarios {sem['fuente_oferta']}")
        n.font = Font(italic=True, color="808080")

    enc = fila + 1
    c = ws.cell(enc, 1, "Hora")
    c.fill, c.font, c.alignment, c.border = F_HORA, BLANCO, CENTRO, BORDE
    for j, dia in enumerate(DIAS_GRILLA, start=2):
        c = ws.cell(enc, j, dia)
        c.fill, c.font, c.alignment, c.border = F_DIA, Font(bold=True), CENTRO, BORDE
    for j, titulo in enumerate(PANEL, start=9):
        c = ws.cell(enc, j, titulo)
        c.fill, c.font, c.alignment, c.border = F_PANEL, BLANCO, CENTRO, BORDE

    # Grilla horaria
    horas = list(range(HORA_INICIO, HORA_FIN + 1))
    for i, h in enumerate(horas):
        r = enc + 1 + i
        c = ws.cell(r, 1, fmt_hora(h * 60))
        c.alignment, c.border = CENTRO, BORDE
        for j in range(2, 8):
            ws.cell(r, j).border = BORDE
    a_confirmar = []
    for m in sem["materias"]:
        relleno, fuente = colores.get(m["plan_id"], (None, None))
        if m["horario_a_confirmar"] and not m["bloques"]:
            a_confirmar.append(m["materia"])
        for b in m["bloques"]:
            if not (1 <= b["dia"] <= 6):
                continue
            for i, h in enumerate(horas):
                if b["desde"] < (h + 1) * 60 and h * 60 < b["hasta"]:
                    c = ws.cell(enc + 1 + i, b["dia"] + 1)
                    texto = m["materia"] + (" (anual)" if m["anual"] else "")
                    c.value = texto if not c.value else f"{c.value} / {texto}"
                    if relleno:
                        c.fill, c.font = relleno, fuente
                    c.alignment = IZQ

    # Panel de materias pendientes
    for i, cand in enumerate(sem["candidatas"]):
        r = enc + 1 + i
        valores = [
            "SI" if cand["cursar"] else "-",
            "SI" if cand["disponible"] else "NO",
            cand["materia"],
            cand["dias"],
            cand["horarios"],
            cand["horas"],
            " - ".join(cand["correlativas_faltantes"]) or (cand["motivo"] if not cand["cursar"] else ""),
        ]
        if cand["cursar"]:
            relleno, fuente = colores.get(cand["plan_id"], (F_DISP, BLANCO))
        elif cand["disponible"]:
            relleno, fuente = F_DISP, BLANCO
        else:
            relleno, fuente = F_NO_DISP, BLANCO
        for j, v in enumerate(valores, start=9):
            c = ws.cell(r, j, v)
            c.border = BORDE
            c.alignment = CENTRO if j in (9, 10, 14) else IZQ
            if j <= 11:
                c.fill, c.font = relleno, fuente

    fin = enc + 1 + max(len(horas), len(sem["candidatas"]))
    total = ws.cell(fin, 13, "Total hs semana")
    total.font = Font(bold=True)
    ws.cell(fin, 14, sem["horas"]).font = Font(bold=True)
    if a_confirmar:
        ws.cell(fin, 1, "Horario a confirmar: " + ", ".join(a_confirmar)).font = Font(italic=True, color="C00000")
    return fin + 3


def _hoja_resumen(ws, rutas, contexto):
    ws["A1"] = "Rutas de cursada"
    ws["A1"].font = Font(bold=True, size=16)
    fila = 3
    for clave, valor in contexto.items():
        ws.cell(fila, 1, clave).font = Font(bold=True)
        ws.cell(fila, 2, valor)
        fila += 1
    fila += 1
    encabezados = ["Ruta", "Semestres", "Finaliza", "Completa", "Descripción", "Sin planificar"]
    for j, e in enumerate(encabezados, start=1):
        c = ws.cell(fila, j, e)
        c.fill, c.font, c.border = F_DIA, BLANCO, BORDE
    for r in rutas:
        fila += 1
        valores = [
            r["nombre"], r["cantidad_semestres"], r["finaliza"] or "-", "SI" if r["completa"] else "NO",
            r["descripcion"], "; ".join(f"{x['materia']} ({x['motivo']})" for x in r["sin_planificar"]),
        ]
        for j, v in enumerate(valores, start=1):
            c = ws.cell(fila, j, v)
            c.border, c.alignment = BORDE, IZQ
    for col, ancho in {"A": 34, "B": 12, "C": 22, "D": 10, "E": 70, "F": 60}.items():
        ws.column_dimensions[col].width = ancho


def rutas_a_excel(rutas: list[dict], contexto: dict | None = None) -> bytes:
    wb = Workbook()
    _hoja_resumen(wb.active, rutas, contexto or {})
    wb.active.title = "Resumen"
    colores = _colores(rutas)
    usados = {"Resumen"}
    for r in rutas:
        ws = wb.create_sheet(_nombre_hoja(r["nombre"], usados))
        for col, ancho in ANCHOS.items():
            ws.column_dimensions[col].width = ancho
        fila = 1
        for sem in r["semestres"]:
            fila = _bloque_semestre(ws, fila, sem, colores)
        if r["sin_planificar"]:
            ws.cell(fila, 1, "Materias que no se pudieron ubicar").font = Font(bold=True, color="C00000")
            for x in r["sin_planificar"]:
                fila += 1
                ws.cell(fila, 1, x["materia"])
                ws.cell(fila, 3, x["motivo"])
        ws.freeze_panes = "B1"
        ws.sheet_view.zoomScale = 80
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()

