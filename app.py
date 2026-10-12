"""
Puente Colgante — Calculadora web con Streamlit
"""

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
import streamlit as st


# ─────────────────────────────────────────
#  Redondeo escolar (mitad hacia arriba)
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
#  Interfaz Streamlit
# ─────────────────────────────────────────

st.set_page_config(
    page_title="Puente Colgante",
    page_icon="🌉",
    layout="wide",
)

st.title("🌉 Calculadora de Puente Colgante")
st.markdown("**Cable parabólico con escala para maqueta** — Ingrese los datos en el panel izquierdo y presione **Calcular**.")

# Inicializar session_state (persiste resultados entre descargas)
for key in ['resultado', 'nombre_prop', 'png_2d', 'png_3d', 'xlsx']:
    if key not in st.session_state:
        st.session_state[key] = None

# ── Panel lateral de entrada ──
with st.sidebar:
    st.header("Datos del puente")

    L = st.number_input(
        "Luz del puente L (metros)",
        min_value=0.1, max_value=5000.0,
        value=100.0, step=1.0, format="%.2f"
    )

    st.markdown("**Proporción de flecha**")
    opcion_prop = st.radio(
        "Seleccione:",
        options=["L/8 — recomendado", "L/6", "L/5 — flecha pronunciada", "Personalizada"],
        label_visibility="collapsed"
    )

    frac = None
    nombre_prop = ""
    if opcion_prop == "L/8 — recomendado":
        frac = 1/8;  nombre_prop = "L/8"
    elif opcion_prop == "L/6":
        frac = 1/6;  nombre_prop = "L/6"
    elif opcion_prop == "L/5 — flecha pronunciada":
        frac = 1/5;  nombre_prop = "L/5"
    else:
        prop_input = st.text_input("Fracción personalizada (ej: 1/7)", value="1/7")
        try:
            if '/' in prop_input:
                num, den = prop_input.split('/')
                frac = float(num) / float(den)
            else:
                frac = float(prop_input)
            nombre_prop = f"L×{frac:.5g}"
            if frac <= 0:
                st.error("La proporción debe ser mayor que cero.")
                frac = None
        except (ValueError, ZeroDivisionError):
            st.error("Fracción inválida. Ejemplo: 1/7")
            frac = None

    maqueta_cm = st.number_input(
        "Longitud de la maqueta (cm)",
        min_value=1.0, max_value=10000.0,
        value=50.0, step=1.0, format="%.1f"
    )

    h0_cm = st.number_input(
        "Holgura central h₀ (cm de maqueta)",
        min_value=0.0, max_value=1000.0,
        value=1.0, step=0.1, format="%.2f",
        help="Altura del cable sobre el tablero en el centro del puente. "
             "El tensor central no puede medir 0 cm, porque el cable necesita amarre.",
    )
    if h0_cm == 0:
        st.warning("Con h₀ = 0 el tensor central mide 0 cm y no se puede construir.")

    calcular_btn = st.button("Calcular", type="primary", use_container_width=True)

# ── Al presionar Calcular: generar todo y guardarlo en session_state ──
if calcular_btn:
    if frac is None:
        st.error("Corrija la proporción de flecha antes de calcular.")
    else:
        with st.spinner("Calculando..."):
            r = calcular(L, frac, maqueta_cm, h0_cm)

            fig2d = graficar_2d(r, nombre_prop)
            buf2d = io.BytesIO()
            fig2d.savefig(buf2d, dpi=150, bbox_inches='tight')
            buf2d.seek(0)

            fig3d = graficar_3d(r)
            buf3d = io.BytesIO()
            fig3d.savefig(buf3d, dpi=150, bbox_inches='tight')
            buf3d.seek(0)

            st.session_state.resultado   = r
            st.session_state.nombre_prop = nombre_prop
            st.session_state.png_2d      = buf2d.getvalue()
            st.session_state.png_3d      = buf3d.getvalue()
            st.session_state.xlsx        = exportar_excel_bytes(r, nombre_prop)

            plt.close('all')

# ── Mostrar resultados desde session_state (persisten en descargas) ──
if st.session_state.resultado is not None:
    r            = st.session_state.resultado
    nombre_prop_s = st.session_state.nombre_prop
    am           = r['a_maqueta']
    f_val        = r['f']
    L_val        = r['L']
    fL           = f_val / L_val
    fL_pct       = fL * 100

    # ── Métricas principales ──
    st.subheader("Parámetros del puente")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Escala  1:E",         r['escala_str'])
    c2.metric("Factor  k",           fmt(r['factor'], 6))
    c3.metric("Proporción",          nombre_prop_s)
    c4.metric("Flecha  f",           f"{fmt(f_val)} m")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Coeficiente  a (m)",  f"{fmt(r['a'], 6)} m⁻¹")
    c6.metric("Coeficiente  a (cm)", f"{fmt(r['a_cm'], 6)} cm⁻¹")
    c7.metric("Holgura  h₀",         f"{fmt(r['h0_cm'], 2)} cm")
    c8.metric("Altura torre  f + h₀ (maqueta)", f"{fmt(am(r['torre']))} cm")

    st.markdown(
        f"**Ecuación del cable:** $y = {fmt(r['a'], 6)}\\,x^2$ (x, y en m) "
        f"— en la maqueta: $y = {fmt(r['a_cm'], 6)}\\,x^2$ (x, y en cm)  \n"
        f"**Tensor:** $T_i = y_i + h_0$, con $h_0 = {fmt(r['h0'])}$ m reales "
        f"$= {fmt(r['h0_cm'], 2)}$ cm de maqueta"
    )

    # ── Aviso técnico con información expandible ──
    if 1/12 <= fL <= 1/8:
        st.success(f"✓  f/L = {fL:.4f} ({fL_pct:.2f}%) — dentro del rango técnico óptimo (1/12 a 1/8).")
        with st.expander("¿Por qué este rango es el óptimo? — haz clic para saber más"):
            st.markdown(f"""
### Relación flecha/luz (f/L) en puentes colgantes

Su valor **f/L = {fL:.4f} ({fL_pct:.2f}%)** se encuentra en el rango estándar que la ingeniería
estructural recomienda para puentes colgantes. Esto se debe a:

| Aspecto | Explicación |
|---|---|
| **Eficiencia del cable** | El cable trabaja casi en tracción pura, su comportamiento más eficiente. |
| **Deformaciones controladas** | Minimiza las deflexiones del tablero bajo cargas variables (viento, tráfico, peatones). |
| **Economía** | Flechas moderadas evitan torres excesivamente altas y cables demasiado largos. |
| **Estabilidad aerodinámica** | El puente es menos sensible a la acción del viento. |
| **Tensión en anclajes** | Las fuerzas horizontales en los anclajes son manejables con tecnología convencional. |

**¿Qué pasa si me salgo del rango?**
- **f/L < 1/12 (< 8.33%):** el cable queda casi horizontal → tensiones horizontales enormes en anclajes.
- **f/L > 1/8 (> 12.50%):** torres muy altas, cables más largos, mayor costo y más sensible al viento.

**Referencias bibliográficas para consultar:**
- Manterola Armisén, J. — *Puentes: Apuntes para su diseño, cálculo y construcción* (UPM, Madrid)
- Jiménez Montoya, P. — *Hormigón Armado*, Ed. Gustavo Gili
- AASHTO LRFD Bridge Design Specifications (sección de puentes colgantes)
- Simiu, E. & Scanlan, R. — *Wind Effects on Structures*, Wiley
            """)
    else:
        if fL < 1/12:
            diagnostico = "flecha muy baja → el cable queda casi horizontal y las tensiones horizontales en los anclajes son excesivamente grandes"
            advertencia = f"Con f/L = {fL:.4f} las fuerzas horizontales son **{round((1/12)/fL, 1)}×** mayores que en el límite inferior del rango óptimo."
            comparacion = "baja"
        else:
            diagnostico = "flecha muy alta → las torres son muy altas, el cable muy largo y el puente es muy sensible al viento"
            advertencia = f"Con f/L = {fL:.4f} la torre alcanza **{f_val:.2f} m**, lo que puede ser desproporcionado para una luz de {L_val:.2f} m."
            comparacion = "alta"

        st.warning(f"⚠  f/L = {fL:.4f} ({fL_pct:.2f}%) — fuera del rango técnico óptimo (1/12 a 1/8).")
        with st.expander("¿Qué implica estar fuera del rango? — haz clic para ver el análisis técnico completo"):
            st.markdown(f"""
### Análisis técnico — f/L = {fL:.4f} ({fL_pct:.2f}%)

**Diagnóstico:** {diagnostico}.

> {advertencia}

---

### ¿Por qué existe un rango óptimo de f/L?

| Relación f/L | Comportamiento del puente |
|---|---|
| **< 1/12 (< 8.33%)** | Cable casi horizontal → tensiones horizontales enormes. Anclajes muy costosos. Alto riesgo estructural. |
| ✅ **1/12 a 1/8 (óptimo)** | **Equilibrio entre eficiencia, costo, deformaciones y estabilidad.** |
| **> 1/8 (> 12.50%)** | Torres muy altas y cables largos → mayor costo. Mayor sensibilidad al viento lateral. |

### Consecuencias específicas para este diseño (f/L = {fL:.4f})

- La flecha real es **{f_val:.3f} m**, lo que es {'muy pequeña' if comparacion == 'baja' else 'muy grande'} para una luz de **{L_val:.2f} m**.
- {'Las fuerzas horizontales en los anclajes son mucho mayores de lo normal.' if comparacion == 'baja' else 'Las torres y los cables requieren materiales y cimientos especiales por su gran tamaño.'}
- Se recomienda **ajustar la proporción** a un valor entre L/12 y L/8, o consultar con un ingeniero estructural.

### Recomendación
Para una luz de **{L_val:.2f} m**, la flecha óptima estaría entre:
- **Mínimo (L/12):** f = {L_val/12:.3f} m
- **Máximo (L/8):**  f = {L_val/8:.3f} m

### Referencias bibliográficas para profundizar:
- Manterola Armisén, J. — *Puentes: Apuntes para su diseño, cálculo y construcción* (UPM, Madrid)
- Jiménez Montoya, P. — *Hormigón Armado*, Ed. Gustavo Gili
- AASHTO LRFD Bridge Design Specifications (sección de puentes colgantes)
- Simiu, E. & Scanlan, R. — *Wind Effects on Structures*, Wiley
            """)

    # ── Resumen de medidas ──
    st.subheader("Resumen de medidas")
    df_resumen = pd.DataFrame([
        ["Luz  L",                    fmt(L_val),                fmt(am(L_val))],
        ["Semiluz  p",                fmt(r['p']),               fmt(am(r['p']))],
        ["Flecha  f",                 fmt(f_val),                fmt(am(f_val))],
        ["Holgura central  h₀",       fmt(r['h0']),              fmt(r['h0_cm'])],
        ["Altura torre  f + h₀",      fmt(r['torre']),           fmt(am(r['torre']))],
        ["Distancia  d",              fmt(r['d']),               fmt(am(r['d']))],
        ["Tensor mínimo (h₀)",        fmt(r['h0']),              fmt(r['h0_cm'])],
        ["Suma de los 17 tensores",   fmt(r['suma_tensores']),   fmt(r['suma_tensores_cm'])],
        ["Longitud aprox. del cable", fmt(r['long_cable']),      fmt(am(r['long_cable']))],
    ], columns=["Medida", "Real (m)", "Maqueta (cm)"])
    st.dataframe(df_resumen, hide_index=True, use_container_width=False)
    st.caption(
        "La suma incluye los 17 tensores: las dos torres (i = 0 e i = 16, altura f + h₀) "
        "y los 15 intermedios. La longitud del cable usa la aproximación "
        "L·(1 + 8/3·(f/L)²); h₀ no la cambia porque solo sube el cable."
    )

    # ── Tabla de 17 puntos ──
    st.subheader("Tabla de 17 puntos")
    df_tabla = pd.DataFrame(r['tabla'], columns=COLUMNAS_TABLA)
    st.dataframe(
        df_tabla, hide_index=True, use_container_width=True,
        column_config={c: st.column_config.NumberColumn(format="%.3f")
                       for c in COLUMNAS_TABLA[1:]},
    )
    st.caption(
        "Tensor = yᵢ + h₀: medida lista para cortar. Para marcar los tensores sobre el tablero "
        "de izquierda a derecha, use «Dist. desde torre izquierda» (xᵢ + p)."
    )

    # ── Gráficas en pestañas ──
    st.subheader("Gráficas")
    tab1, tab2 = st.tabs(["Vista 2D — Perfil del cable", "Vista 3D — Perspectiva"])

    with tab1:
        st.image(st.session_state.png_2d, use_container_width=True)

    with tab2:
        st.image(st.session_state.png_3d, use_container_width=True)
        st.caption(
            f"La figura muestra el puente a escala real. "
            f"La persona de 1.80 m junto a la torre permite comparar proporciones. "
            f"Altura de torre sobre el tablero (f + h₀): {fmt(r['torre'], 2)} m."
        )

    # ── Descargas (usan session_state → no recalculan nada) ──
    st.subheader("Descargar resultados")
    st.info("Puedes descargar los tres archivos sin necesidad de volver a calcular.")
    col_a, col_b, col_c = st.columns(3)

    col_a.download_button(
        label="⬇ Gráfica 2D (PNG)",
        data=st.session_state.png_2d,
        file_name="puente_colgante_2d.png",
        mime="image/png",
        use_container_width=True,
    )
    col_b.download_button(
        label="⬇ Gráfica 3D (PNG)",
        data=st.session_state.png_3d,
        file_name="puente_colgante_3d.png",
        mime="image/png",
        use_container_width=True,
    )
    col_c.download_button(
        label="⬇ Tabla Excel (.xlsx)",
        data=st.session_state.xlsx,
        file_name="puente_colgante.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
