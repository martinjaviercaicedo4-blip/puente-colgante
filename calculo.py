"""Cálculo del puente colgante (sin dependencias de Streamlit)."""
from decimal import Decimal, ROUND_HALF_UP


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
