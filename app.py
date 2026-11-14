"""
Puente Colgante — Calculadora web con Streamlit
"""

import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


from calculo import (_decimal, redondear, fmt, COLUMNAS_TABLA, calcular,
                     graficar_2d, graficar_3d, exportar_excel_bytes)




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
