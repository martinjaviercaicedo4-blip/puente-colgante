"""Cálculo del puente colgante, gráficas y Excel (sin dependencias de Streamlit)."""
import io
from decimal import Decimal, ROUND_HALF_UP
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def _decimal(v, decimales):
    # round(v, 10) elimina el ruido binario (1.5624999999 → 1.5625) antes de redondear
    q = Decimal(1).scaleb(-decimales)
    return Decimal(str(round(v, 10))).quantize(q, rounding=ROUND_HALF_UP)


def redondear(v, decimales=3):
    """Redondeo escolar: 1.5625 → 1.563 (round() de Python daría 1.562)."""
    return float(_decimal(v, decimales))


def fmt(v, decimales=3):
    """Texto con redondeo escolar y número fijo de decimales."""
    return f"{_decimal(v, decimales):f}"


# ─────────────────────────────────────────
#  Cálculo central
# ─────────────────────────────────────────

COLUMNAS_TABLA = [
    "i",
    "x real (m)", "y real (m)", "Tensor real (m)",
    "Dist. desde torre izquierda (m)", "Dist. desde torre derecha (m)",
    "x maqueta (cm)", "y maqueta (cm)", "Tensor maqueta (cm)",
    "Dist. desde torre izquierda (cm)", "Dist. desde torre derecha (cm)",
]


def calcular(L, frac, maqueta_cm, h0_cm):
    factor = maqueta_cm / (L * 100)
    denom = int(_decimal(1 / factor, 0))
    escala_str = f"1 : {denom}"
    f  = frac * L
    p  = L / 2
    d  = L / 16
    a  = f / (p ** 2)

    def a_maqueta(metros):
        return metros * 100 * factor

    # La holgura se da en cm de maqueta; en el puente real equivale a h0_cm / (100·k) m
    h0 = h0_cm / (100 * factor)

    tabla = []
    for i in range(17):
        xi = -p + i * d
        yi = a * xi ** 2
        ti = yi + h0
        izq = xi + p
        der = L - i * d
        tabla.append((
            i,
            redondear(xi), redondear(yi), redondear(ti),
            redondear(izq), redondear(der),
            redondear(a_maqueta(xi)), redondear(a_maqueta(yi)), redondear(a_maqueta(ti)),
            redondear(a_maqueta(izq)), redondear(a_maqueta(der)),
        ))

    # Suma de los 17 tensores (las torres en i = 0 e i = 16 incluidas),
    # sumando los valores redondeados de la tabla para que coincida al verificar a mano
    suma_tensores    = float(sum(Decimal(str(row[3])) for row in tabla))
    suma_tensores_cm = float(sum(Decimal(str(row[8])) for row in tabla))

    # Longitud aproximada del cable parabólico: L·(1 + 8/3·(f/L)²)
    long_cable = L * (1 + 8 / 3 * (f / L) ** 2)

    return {
        'L': L, 'f': f, 'p': p, 'd': d, 'a': a,
        'a_cm': a / (100 * factor),
        'h0': h0, 'h0_cm': h0_cm,
        'torre': f + h0,
        'factor': factor, 'denom': denom, 'escala_str': escala_str,
        'maqueta_cm': maqueta_cm,
        'tabla': tabla,
        'suma_tensores': suma_tensores,
        'suma_tensores_cm': suma_tensores_cm,
        'long_cable': long_cable,
        'a_maqueta': a_maqueta,
    }


# ─────────────────────────────────────────
#  Gráfica 2D
# ─────────────────────────────────────────

def graficar_2d(r, nombre_prop):
    L, f, p, d, a = r['L'], r['f'], r['p'], r['d'], r['a']
    h0   = r['h0']
    am   = r['a_maqueta']
    tabla = r['tabla']

    xs_r = np.linspace(-p, p, 400)
    ys_r = a * xs_r ** 2 + h0
    xs_m = [am(x) for x in xs_r]
    ys_m = [am(y) for y in ys_r]

    titulo_base = (f"Puente colgante  |  y = {fmt(a, 4)}·x²  |  tensor = y + h₀  "
                   f"|  L = {fmt(L, 2)} m  |  f = {fmt(f)} m  |  h₀ = {fmt(h0)} m")

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    fig.suptitle(titulo_base, fontsize=12, fontweight='bold')

    paneles = [
        {
            'ax': axes[0],
            'titulo': f"Escala real — {r['escala_str']}",
            'xs_curva': xs_r, 'ys_curva': ys_r,
            'pts_x': [row[1] for row in tabla],
            'pts_y': [row[3] for row in tabla],
            'p_val': p, 't_val': f + h0, 'h0_val': h0,
            'xlabel': 'x (m)', 'ylabel': 'altura sobre el tablero (m)',
            'info_d': f"d = L/16 = {fmt(d)} m",
        },
        {
            'ax': axes[1],
            'titulo': f"Escala maqueta — {r['maqueta_cm']:.1f} cm",
            'xs_curva': xs_m, 'ys_curva': ys_m,
            'pts_x': [row[6] for row in tabla],
            'pts_y': [row[8] for row in tabla],
            'p_val': am(p), 't_val': am(f + h0), 'h0_val': am(h0),
            'xlabel': 'x (cm)', 'ylabel': 'altura sobre el tablero (cm)',
            'info_d': f"d = L/16 = {fmt(am(d))} cm",
        },
    ]

    for pan in paneles:
        ax  = pan['ax']
        pv  = pan['p_val']
        fv  = pan['t_val']
        hv  = pan['h0_val']

        ax.plot(pan['xs_curva'], pan['ys_curva'],
                color='steelblue', linewidth=2.2, label='Cable (parábola)', zorder=3)
        ax.scatter(pan['pts_x'], pan['pts_y'],
                   color='steelblue', s=40, zorder=5, label='Puntos tabla')
        ax.axhline(0, color='saddlebrown', linewidth=2.0,
                   linestyle='-', label='Tablero', zorder=2)

        torres_x = {round(pv, 6), round(-pv, 6)}
        for xi, yi in zip(pan['pts_x'], pan['pts_y']):
            if round(abs(xi), 6) in torres_x:
                continue
            ax.plot([xi, xi], [0, yi],
                    color='cornflowerblue', linewidth=0.9, linestyle='--', zorder=2)

        for signo in [-1, 1]:
            tx, ty = signo * pv, fv
            ax.plot([tx, tx], [0, ty], color='darkorange', linewidth=3.5,
                    linestyle='-', zorder=4,
                    label='Torre' if signo == -1 else '_nolegend_')
            ax.annotate(f"Torre ({fmt(tx, 2)}, {fmt(ty, 2)})",
                        xy=(tx, ty),
                        xytext=(tx + pv * 0.04, ty + fv * 0.04),
                        fontsize=8, color='darkorange',
                        arrowprops=dict(arrowstyle='->', color='darkorange', lw=0.8))

        ax.scatter([0], [hv], color='red', s=90, zorder=6)
        ax.annotate(f"V(0, {fmt(hv)})  tensor = h₀", xy=(0, hv),
                    xytext=(pv * 0.05, hv + fv * 0.12),
                    fontsize=9, color='red',
                    arrowprops=dict(arrowstyle='->', color='red', lw=1))

        ax.text(0.02, 0.97, pan['info_d'], transform=ax.transAxes,
                fontsize=9, verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow',
                          edgecolor='gray', alpha=0.85))

        ax.set_xlabel(pan['xlabel'])
        ax.set_ylabel(pan['ylabel'])
        ax.set_title(pan['titulo'])
        ax.set_aspect('equal')
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(fontsize=8, loc='upper center')

    plt.tight_layout()
    return fig


# ─────────────────────────────────────────
#  Gráfica 3D
# ─────────────────────────────────────────

def graficar_3d(r):
    L, f, p, d, a = r['L'], r['f'], r['p'], r['d'], r['a']
    h0 = r['h0']
    ht = f + h0   # altura de la torre sobre el tablero

    # Ancho del tablero ~ L/10, con mínimo razonable
    bw = max(L / 10, 1.5)

    fig = plt.figure(figsize=(16, 7))
    ax  = fig.add_subplot(111, projection='3d')

    xs = np.linspace(-p, p, 300)
    zs = a * xs ** 2 + h0

    # ── Cables principales (uno a cada lado) ──
    for ys, lbl in [(-bw/2, 'Cable principal'), (bw/2, '_')]:
        ax.plot(xs, [ys]*len(xs), zs,
                color='steelblue', linewidth=2.0, label=lbl)

    # ── Tablero (superficie plana en z=0) ──
    verts = [list(zip([-p, p, p, -p],
                      [-bw/2, -bw/2, bw/2, bw/2],
                      [0, 0, 0, 0]))]
    deck = Poly3DCollection(verts, alpha=0.60,
                            facecolor='#BEBEBE', edgecolor='dimgray')
    ax.add_collection3d(deck)
    for ys in [-bw/2, bw/2]:
        ax.plot([-p, p], [ys, ys], [0, 0],
                color='saddlebrown', linewidth=1.8,
                label='Tablero' if ys < 0 else '_')

    # ── Torres en x = ±p ──
    for tx in [-p, p]:
        for ty in [-bw/2, bw/2]:
            ax.plot([tx, tx], [ty, ty], [0, ht],
                    color='darkorange', linewidth=3.5,
                    label='Torre' if (tx == -p and ty == -bw/2) else '_')
        ax.plot([tx, tx], [-bw/2, bw/2], [ht,      ht     ], color='darkorange', linewidth=2.5)
        ax.plot([tx, tx], [-bw/2, bw/2], [ht*0.55, ht*0.55], color='darkorange', linewidth=1.8)

    # ── Tensores cada d metros ──
    for i in range(17):
        xi = -p + i * d
        zi = a * xi ** 2 + h0
        for ys in [-bw/2, bw/2]:
            ax.plot([xi, xi], [ys, ys], [0, zi],
                    color='lightsteelblue', linewidth=0.7,
                    linestyle='--', alpha=0.8,
                    label='Tensor' if (i == 1 and ys < 0) else '_')

    # ── Persona de 1.80 m junto a la torre derecha ──
    ph = 1.80
    px = p + bw * 0.35
    py = 0.0

    ax.plot([px, px], [py, py], [0, ph*0.82],
            color='#8B0000', linewidth=2.5, label='Persona 1.80 m')
    ax.scatter([px], [py], [ph], color='#8B0000', s=80)
    ax.plot([px - bw*0.06, px + bw*0.06], [py, py], [ph*0.60]*2,
            color='#8B0000', linewidth=1.8)
    ax.plot([px, px - bw*0.04], [py, py], [ph*0.44, 0], color='#8B0000', linewidth=1.8)
    ax.plot([px, px + bw*0.04], [py, py], [ph*0.44, 0], color='#8B0000', linewidth=1.8)

    # Cota persona
    ax.plot([px + bw*0.10]*2, [py, py], [0, ph],
            color='#8B0000', linewidth=0.8, linestyle=':')
    ax.text(px + bw*0.13, py, ph/2, '1.80 m',
            fontsize=7, color='#8B0000', fontweight='bold')
    ax.text(p, bw/2 + bw*0.15, ht*1.04,
            f'Torre {fmt(ht, 2)} m', fontsize=7, color='darkorange', fontweight='bold')

    ax.set_xlabel('Longitud (m)', labelpad=8)
    ax.set_ylabel('Ancho (m)',    labelpad=8)
    ax.set_zlabel('Altura (m)',   labelpad=8)
    ax.set_title(
        f'Vista 3D a escala real  —  L = {fmt(L, 2)} m  |  f = {fmt(f)} m  |  h₀ = {fmt(h0)} m  |  {r["escala_str"]}',
        fontsize=10, fontweight='bold', pad=12
    )

    ax.view_init(elev=22, azim=-50)

    # Límites de cada eje en metros reales
    x_lo, x_hi = -p,       p + bw*0.55
    y_lo, y_hi = -bw*1.1,  bw*1.1
    z_lo, z_hi =  0,        ht * 1.35
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.set_zlim(z_lo, z_hi)

    # Aspecto proporcional: cada metro ocupa el mismo espacio en los tres ejes
    ax.set_box_aspect([x_hi - x_lo, y_hi - y_lo, z_hi - z_lo])

    ax.legend(loc='upper left', fontsize=7)
    plt.tight_layout()
    return fig


# ─────────────────────────────────────────
#  Exportación Excel (devuelve bytes)
# ─────────────────────────────────────────

def exportar_excel_bytes(r, nombre_prop):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultados"

    azul_oscuro = PatternFill("solid", fgColor="1F497D")
    azul_medio  = PatternFill("solid", fgColor="BDD7EE")
    borde_fino  = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    fmt3 = '0.000'

    def celda(ws, fila, col, valor, bold=False, fill=None, align='center', fmt=None):
        c = ws.cell(row=fila, column=col, value=valor)
        c.font = Font(name='Calibri', bold=bold,
                      color="FFFFFF" if fill == azul_oscuro else "000000")
        c.alignment = Alignment(horizontal=align, vertical='center')
        c.border = borde_fino
        if fill:
            c.fill = fill
        if fmt:
            c.number_format = fmt
        return c

    L, f, p, d, a = r['L'], r['f'], r['p'], r['d'], r['a']
    h0 = r['h0']
    am = r['a_maqueta']
    fmt6 = '0.000000'
    n_cols = len(COLUMNAS_TABLA)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_cols)
    c = ws['A1']
    c.value = "PUENTE COLGANTE — Calculadora de cable parabólico"
    c.font = Font(name='Calibri', bold=True, size=14, color="FFFFFF")
    c.fill = azul_oscuro
    c.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 24

    fila = 3
    celda(ws, fila, 1, "PARÁMETRO", bold=True, fill=azul_medio)
    celda(ws, fila, 2, "VALOR",     bold=True, fill=azul_medio)
    celda(ws, fila, 3, "UNIDAD",    bold=True, fill=azul_medio)
    fila += 1
    for nombre, valor, unidad, formato in [
        ("Factor de escala  k",  redondear(r['factor'], 6), "",     fmt6),
        ("Escala  1:E",          r['escala_str'],           "",     None),
        ("Proporción flecha",    nombre_prop,               "",     None),
        ("Coeficiente  a",       redondear(a, 6),           "m⁻¹",  fmt6),
        ("Coeficiente  a",       redondear(r['a_cm'], 6),   "cm⁻¹", fmt6),
        ("Ecuación del cable",   f"y = {fmt(a, 6)}·x²",     "m",    None),
        ("Tensor",               "Tᵢ = yᵢ + h₀",            "",     None),
    ]:
        celda(ws, fila, 1, nombre, align='left')
        celda(ws, fila, 2, valor, fmt=formato)
        celda(ws, fila, 3, unidad)
        fila += 1

    fila += 1
    celda(ws, fila, 1, "MEDIDA",       bold=True, fill=azul_medio)
    celda(ws, fila, 2, "REAL (m)",     bold=True, fill=azul_medio)
    celda(ws, fila, 3, "MAQUETA (cm)", bold=True, fill=azul_medio)
    fila += 1
    for nombre_m, real, maq in [
        ("Luz  L",                     L,                     am(L)),
        ("Semiluz  p",                 p,                     am(p)),
        ("Flecha  f",                  f,                     am(f)),
        ("Holgura central  h₀",        h0,                    r['h0_cm']),
        ("Altura torre  f + h₀",       r['torre'],            am(r['torre'])),
        ("Distancia  d",               d,                     am(d)),
        ("Tensor mínimo (h₀)",         h0,                    r['h0_cm']),
        ("Suma de los 17 tensores",    r['suma_tensores'],    r['suma_tensores_cm']),
        ("Longitud aprox. del cable",  r['long_cable'],       am(r['long_cable'])),
    ]:
        celda(ws, fila, 1, nombre_m, align='left')
        celda(ws, fila, 2, redondear(real), fmt=fmt3)
        celda(ws, fila, 3, redondear(maq),  fmt=fmt3)
        fila += 1

    fila += 1
    for col, h in enumerate(COLUMNAS_TABLA, 1):
        celda(ws, fila, col, h, bold=True, fill=azul_oscuro)
    fila += 1

    alt_fill = PatternFill("solid", fgColor="DEEAF1")
    for idx, row in enumerate(r['tabla']):
        fill_row = alt_fill if idx % 2 == 0 else None
        for col, val in enumerate(row, 1):
            celda(ws, fila, col, val, fill=fill_row, fmt=fmt3 if col > 1 else None)
        fila += 1

    ws.column_dimensions['A'].width = 26
    for i in range(2, n_cols + 1):
        ws.column_dimensions[get_column_letter(i)].width = 20

    ws2 = wb.create_sheet("Info técnica")
    ws2['A1'] = "Relación f/L"
    ws2['B1'] = f / L
    ws2['B1'].number_format = '0.0000'
    ws2['A2'] = "Rango óptimo (1/12 a 1/8)"
    ws2['B2'] = "0.0833 … 0.1250"
    ws2['A3'] = "¿Dentro del rango?"
    ws2['B3'] = "Sí" if (1/12 <= f/L <= 1/8) else "No — fuera del rango técnico"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


