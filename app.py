"""
Puente Colgante — Calculadora web con Streamlit
"""

import io
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
#  Cálculo central
# ─────────────────────────────────────────

def calcular(L, frac, maqueta_cm):
    factor = maqueta_cm / (L * 100)
    denom = round(1 / factor)
    escala_str = f"1 : {denom}"
    f  = frac * L
    p  = L / 2
    d  = L / 16
    a  = f / (p ** 2)

    def a_maqueta(metros):
        return metros * 100 * factor

    tabla = []
    for i in range(17):
        xi = -p + i * d
        yi = a * xi ** 2
        di = L - i * d
        tabla.append((
            i,
            round(xi, 3), round(yi, 3),
            round(a_maqueta(xi), 3), round(a_maqueta(yi), 3),
            round(di, 3), round(a_maqueta(di), 3),
        ))

    return {
        'L': L, 'f': f, 'p': p, 'd': d, 'a': a,
        'factor': factor, 'escala_str': escala_str,
        'maqueta_cm': maqueta_cm,
        'tabla': tabla,
        'a_maqueta': a_maqueta,
    }


# ─────────────────────────────────────────
#  Gráfica 2D
# ─────────────────────────────────────────

def graficar_2d(r, nombre_prop):
    L, f, p, d, a = r['L'], r['f'], r['p'], r['d'], r['a']
    am   = r['a_maqueta']
    tabla = r['tabla']

    xs_r = np.linspace(-p, p, 400)
    ys_r = a * xs_r ** 2
    xs_m = [am(x) for x in xs_r]
    ys_m = [am(y) for y in ys_r]

    titulo_base = (f"Puente colgante  |  f(x) = {a:.4f}·x²  "
                   f"|  L = {L:.2f} m  |  f = {f:.3f} m")

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    fig.suptitle(titulo_base, fontsize=12, fontweight='bold')

    paneles = [
        {
            'ax': axes[0],
            'titulo': f"Escala real — {r['escala_str']}",
            'xs_curva': xs_r, 'ys_curva': ys_r,
            'pts_x': [row[1] for row in tabla],
            'pts_y': [row[2] for row in tabla],
            'p_val': p, 'f_val': f,
            'xlabel': 'x (m)', 'ylabel': 'y (m)',
            'info_d': f"d = L/16 = {d:.3f} m",
        },
        {
            'ax': axes[1],
            'titulo': f"Escala maqueta — {r['maqueta_cm']:.1f} cm",
            'xs_curva': xs_m, 'ys_curva': ys_m,
            'pts_x': [row[3] for row in tabla],
            'pts_y': [row[4] for row in tabla],
            'p_val': am(p), 'f_val': am(f),
            'xlabel': 'x (cm)', 'ylabel': 'y (cm)',
            'info_d': f"d = L/16 = {am(d):.3f} cm",
        },
    ]

    for pan in paneles:
        ax  = pan['ax']
        pv  = pan['p_val']
        fv  = pan['f_val']

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
            ax.annotate(f"Torre ({tx:.2f}, {ty:.2f})",
                        xy=(tx, ty),
                        xytext=(tx + pv * 0.04, ty + fv * 0.04),
                        fontsize=8, color='darkorange',
                        arrowprops=dict(arrowstyle='->', color='darkorange', lw=0.8))

        ax.scatter([0], [0], color='red', s=90, zorder=6)
        ax.annotate("V(0, 0)  tensor=0", xy=(0, 0),
                    xytext=(pv * 0.05, fv * 0.12),
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
        ax.legend(fontsize=8)

    plt.tight_layout()
    return fig


# ─────────────────────────────────────────
#  Gráfica 3D
# ─────────────────────────────────────────

def graficar_3d(r):
    L, f, p, d, a = r['L'], r['f'], r['p'], r['d'], r['a']

    # Ancho del tablero ~ L/10, con mínimo razonable
    bw = max(L / 10, 1.5)

    fig = plt.figure(figsize=(16, 7))
    ax  = fig.add_subplot(111, projection='3d')

    xs = np.linspace(-p, p, 300)
    zs = a * xs ** 2

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
            ax.plot([tx, tx], [ty, ty], [0, f],
                    color='darkorange', linewidth=3.5,
                    label='Torre' if (tx == -p and ty == -bw/2) else '_')
        ax.plot([tx, tx], [-bw/2, bw/2], [f,      f     ], color='darkorange', linewidth=2.5)
        ax.plot([tx, tx], [-bw/2, bw/2], [f*0.55, f*0.55], color='darkorange', linewidth=1.8)

    # ── Tensores cada d metros ──
    for i in range(17):
        xi = -p + i * d
        zi = a * xi ** 2
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
    ax.text(p, bw/2 + bw*0.15, f*1.04,
            f'Torre {f:.2f} m', fontsize=7, color='darkorange', fontweight='bold')

    ax.set_xlabel('Longitud (m)', labelpad=8)
    ax.set_ylabel('Ancho (m)',    labelpad=8)
    ax.set_zlabel('Altura (m)',   labelpad=8)
    ax.set_title(
        f'Vista 3D a escala real  —  L = {L:.2f} m  |  f = {f:.3f} m  |  {r["escala_str"]}',
        fontsize=10, fontweight='bold', pad=12
    )

    ax.view_init(elev=22, azim=-50)

    # Límites de cada eje en metros reales
    x_lo, x_hi = -p,       p + bw*0.55
    y_lo, y_hi = -bw*1.1,  bw*1.1
    z_lo, z_hi =  0,        f * 1.35
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
    am = r['a_maqueta']

    ws.merge_cells('A1:G1')
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
    for nombre, valor, unidad in [
        ("Escala",            r['escala_str'],        ""),
        ("Proporción flecha", nombre_prop,             ""),
        ("Constante  a",      a,                      "m⁻¹"),
        ("Función",           f"f(x) = {a:.6f}·x²",  ""),
    ]:
        celda(ws, fila, 1, nombre, align='left')
        if isinstance(valor, float):
            celda(ws, fila, 2, valor, fmt=fmt3)
        else:
            celda(ws, fila, 2, valor)
        celda(ws, fila, 3, unidad)
        fila += 1

    fila += 1
    celda(ws, fila, 1, "MEDIDA",       bold=True, fill=azul_medio)
    celda(ws, fila, 2, "REAL (m)",     bold=True, fill=azul_medio)
    celda(ws, fila, 3, "MAQUETA (cm)", bold=True, fill=azul_medio)
    fila += 1
    for nombre_m, real, maq in [
        ("Luz  L",        L,   am(L)),
        ("Semiluz  p",    p,   am(p)),
        ("Flecha  f",     f,   am(f)),
        ("Distancia  d",  d,   am(d)),
        ("Tensor mínimo", 0.0, 0.0),
        ("Tensor máximo", f,   am(f)),
    ]:
        celda(ws, fila, 1, nombre_m, align='left')
        celda(ws, fila, 2, real, fmt=fmt3)
        celda(ws, fila, 3, maq,  fmt=fmt3)
        fila += 1

    fila += 1
    for col, h in enumerate([
        "i", "x real (m)", "y real (m)",
        "x maqueta (cm)", "y maqueta (cm)",
        "Dist. Tensores (m)", "Dist. Tensores (cm)",
    ], 1):
        celda(ws, fila, col, h, bold=True, fill=azul_oscuro)
    fila += 1

    alt_fill = PatternFill("solid", fgColor="DEEAF1")
    for idx, row in enumerate(r['tabla']):
        fill_row = alt_fill if idx % 2 == 0 else None
        for col, val in enumerate(row, 1):
            celda(ws, fila, col, val, fill=fill_row, fmt=fmt3 if col > 1 else None)
        fila += 1

    for i, ancho in enumerate([6, 14, 14, 18, 18, 18, 22], 1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

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

    calcular_btn = st.button("Calcular", type="primary", use_container_width=True)

# ── Al presionar Calcular: generar todo y guardarlo en session_state ──
if calcular_btn:
    if frac is None:
        st.error("Corrija la proporción de flecha antes de calcular.")
    else:
        with st.spinner("Calculando..."):
            r = calcular(L, frac, maqueta_cm)

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
    c1.metric("Escala",       r['escala_str'])
    c2.metric("Proporción",   nombre_prop_s)
    c3.metric("Flecha  f",    f"{f_val:.3f} m")
    c4.metric("Constante  a", f"{r['a']:.6f}")

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
        ["Luz  L",        f"{L_val:.3f}",      f"{am(L_val):.3f}"],
        ["Semiluz  p",    f"{r['p']:.3f}",      f"{am(r['p']):.3f}"],
        ["Flecha  f",     f"{f_val:.3f}",        f"{am(f_val):.3f}"],
        ["Distancia  d",  f"{r['d']:.3f}",       f"{am(r['d']):.3f}"],
        ["Tensor mínimo", "0.000",                "0.000"],
        ["Tensor máximo", f"{f_val:.3f}",         f"{am(f_val):.3f}"],
    ], columns=["Medida", "Real (m)", "Maqueta (cm)"])
    st.dataframe(df_resumen, hide_index=True, use_container_width=False)

    # ── Tabla de 17 puntos ──
    st.subheader("Tabla de 17 puntos")
    df_tabla = pd.DataFrame(r['tabla'], columns=[
        "i",
        "x real (m)", "y real (m)",
        "x maqueta (cm)", "y maqueta (cm)",
        "Dist. Tensores (m)", "Dist. Tensores (cm)",
    ])
    st.dataframe(df_tabla, hide_index=True, use_container_width=True)

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
            f"Altura de torre: {f_val:.2f} m."
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
