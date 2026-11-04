"""Genera PDFs de oferta sintéticos (formato definido y no definido) para los tests."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

ESTILO = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("FONTSIZE", (0, 0), (-1, -1), 6)])

DEFINIDO = [
    ["Sede Campus: Los Polvorines", "", "", "", "", "", "", "", "", "", "", "", ""],
    ["Códig o Activid ad", "Actividad", "Comisión", "Inicio", "Fin", "Día", "Horario", "Docentes",
     "Aula", "Edificación", "Compartido con", "Tipo clase", "Instancia"],
    ["A0101", "BASES DE DATOS II (A0101)", "A0101-COM-01", "16/03/2026", "04/07/2026", "Lunes", "18:00 a 22:00",
     "Juan Pérez", "Aula 5", "Módulo 7", "", "Teórica", "Regular"],
    ["A0101", "BASES DE DATOS II (A0101)", "A0101-COM-01", "16/03/2026", "04/07/2026", "Jueves", "18:00 a 22:00",
     "Ana Gómez", "Lab 3", "Módulo 7", "", "Práctica", "Regular"],
    ["A0101", "BASES DE DATOS II (A0101)", "A0101-COM-02", "16/03/2026", "04/07/2026", "Sábado", "08:00 a 12:00",
     "Juan Pérez", "Aula 2", "Módulo 1", "", "Teórico-Práctica", "Regular"],
    ["A0200", "PROBABILIDAD Y ESTADÍSTICA", "A0200-COM-01", "16/03/2026", "04/07/2026", "Martes", "18:00 a 22:00",
     "María López", "Aula 9", "Módulo 3", "TSIG", "Teórica", "Regular"],
    ["", "", "", "", "", "Jueves", "18:00 a 20:00", "María López", "Aula 9", "Módulo 3", "", "Práctica", ""],
]
NO_DEFINIDO = [
    ["Oferta Académica 1° semestre 2026", "", "", "", ""],
    ["Materias Semestrales", "", "", "", ""],
    ["Actividad", "Comisión", "Día", "Horario", "Modalidad"],
    ["BASES DE DATOS II (A0101)", "COM-01", "Lunes", "18 a 22", "Presencial"],
    ["", "", "Jueves", "18 a 22", ""],
    ["", "COM-02", "Sábado", "8 a 12", "Presencial"],
    ["PROBABILIDAD Y ESTADÍSTICA (A0200)", "COM-01", "Martes", "18 a 22", "Presencial"],
]


def generar(destino, filas):
    doc = SimpleDocTemplate(str(destino), pagesize=landscape(A4))
    t = Table(filas)
    t.setStyle(ESTILO)
    doc.build([t])
    return destino


if __name__ == "__main__":
    import sys
    generar(sys.argv[1], DEFINIDO)
    generar(sys.argv[2], NO_DEFINIDO)
