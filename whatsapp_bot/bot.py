"""Bot de WhatsApp (Cloud API de Meta) que responde con Claude.

Variables de entorno requeridas:
  ANTHROPIC_API_KEY      clave de la API de Anthropic
  WHATSAPP_TOKEN         token de acceso de la WhatsApp Cloud API
  WHATSAPP_PHONE_ID      ID del número de teléfono de WhatsApp Business
  WHATSAPP_VERIFY_TOKEN  texto cualquiera que tú eliges para verificar el webhook
  WHATSAPP_APP_SECRET    (recomendado) secreto de la app de Meta, valida la firma
Opcionales:
  CLAUDE_MODEL           por defecto claude-sonnet-5-5
"""
import hashlib
import hmac
import io
import os
from collections import defaultdict, deque

import anthropic
import requests
from flask import Flask, abort, request

from calculo import calcular, exportar_excel_bytes, fmt, graficar_2d, graficar_3d

import matplotlib.pyplot as plt

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
GRAPH_URL = "https://graph.facebook.com/v21.0/{phone_id}/messages"
SYSTEM = (
    "Eres un asistente por WhatsApp para ingeniería de puentes colgantes "
    "(catenaria, parábola, flecha, tensiones, holgura). Responde en español, "
    "breve y claro, sin formato markdown complejo. Para cualquier cálculo del "
    "puente usa SIEMPRE la herramienta calcular_puente; nunca calcules a mano. "
    "Si falta un dato (luz L, proporción de flecha, longitud de la maqueta, "
    "holgura h0), pídelo antes de calcular."
)

TOOLS = [{
    "name": "calcular_puente",
    "description": (
        "Calcula un puente colgante de cable parabólico con 17 tensores y su escala "
        "de maqueta: flecha, escala, longitud del cable, altura de torre y, para "
        "cada tensor, posición x, altura y, longitud del tensor y distancias desde "
        "ambas torres (real en m y maqueta en cm)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "L": {"type": "number", "description": "Luz del puente en metros (0.1 a 5000)"},
            "flecha": {"type": "number", "description": "Proporción de flecha f/L, p. ej. 0.125 para L/8, 0.1667 para L/6, 0.2 para L/5"},
            "maqueta_cm": {"type": "number", "description": "Longitud de la maqueta en cm"},
            "h0_cm": {"type": "number", "description": "Holgura central h0 en cm de maqueta (mayor que 0)"},
            "enviar_archivos": {"type": "boolean", "description": "true para enviar por WhatsApp las gráficas 2D y 3D y el Excel con la tabla completa. Úsalo si el usuario los pide; si no, ofrécelos al final."},
        },
        "required": ["L", "flecha", "maqueta_cm", "h0_cm"],
    },
}]


def make_files(r, nombre) -> list:
    files = []
    for fname, fn in (('grafica_2d.png', graficar_2d), ('grafica_3d.png', None)):
        fig = fn(r, nombre) if fn else graficar_3d(r)
        buf = io.BytesIO()
        fig.savefig(buf, dpi=150, bbox_inches='tight', format='png')
        plt.close(fig)
        files.append((fname, buf.getvalue(), 'image/png'))
    files.append(('puente_colgante.xlsx', exportar_excel_bytes(r, nombre),
                  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
    return files


def run_bridge_tool(args: dict, outbox: list) -> str:
    try:
        L, frac = float(args["L"]), float(args["flecha"])
        maq, h0 = float(args["maqueta_cm"]), float(args["h0_cm"])
        if not (0.1 <= L <= 5000 and frac > 0 and maq > 0 and h0 >= 0):
            return "Error: valores fuera de rango."
        r = calcular(L, frac, maq, h0)
        if args.get("enviar_archivos"):
            outbox.extend(make_files(r, f"L×{frac:.5g}"))
    except (KeyError, ValueError, TypeError) as e:
        return f"Error en los datos: {e}"
    lines = [
        f"Escala {r['escala_str']}; flecha f={fmt(r['f'])} m; torre={fmt(r['torre'])} m; "
        f"h0 real={fmt(r['h0'])} m; cable aprox={fmt(r['long_cable'])} m; "
        f"suma tensores={fmt(r['suma_tensores'])} m ({fmt(r['suma_tensores_cm'])} cm maqueta).",
        "i | x(m) | y(m) | tensor(m) | desde torre izq(m) | desde torre der(m) | tensor maqueta(cm) | izq maqueta(cm)",
    ]
    for t in r["tabla"]:
        lines.append(f"{t[0]} | {fmt(t[1])} | {fmt(t[2])} | {fmt(t[3])} | {fmt(t[4])} | {fmt(t[5])} | {fmt(t[8])} | {fmt(t[9])}")
    if outbox:
        lines.append("Las gráficas 2D/3D y el Excel se enviarán al usuario automáticamente.")
    return "\n".join(lines)

app = Flask(__name__)
client = anthropic.Anthropic()
history = defaultdict(lambda: deque(maxlen=20))  # memoria por número (en RAM)
seen = deque(maxlen=500)  # ids de mensajes ya procesados (WhatsApp reintenta)


def send(to: str, text: str) -> None:
    requests.post(
        GRAPH_URL.format(phone_id=os.environ["WHATSAPP_PHONE_ID"]),
        headers={"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}"},
        json={"messaging_product": "whatsapp", "to": to, "text": {"body": text[:4000]}},
        timeout=15,
    ).raise_for_status()


def send_file(to: str, name: str, data: bytes, mime: str) -> None:
    """Sube el archivo a WhatsApp y lo envía como imagen o documento."""
    h = {"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}"}
    base = GRAPH_URL.format(phone_id=os.environ["WHATSAPP_PHONE_ID"])
    up = requests.post(
        base.replace("/messages", "/media"), headers=h,
        data={"messaging_product": "whatsapp", "type": mime},
        files={"file": (name, data, mime)}, timeout=60,
    )
    up.raise_for_status()
    kind = "image" if mime.startswith("image/") else "document"
    media = {"id": up.json()["id"]}
    if kind == "document":
        media["filename"] = name
    requests.post(
        base, headers=h, timeout=15,
        json={"messaging_product": "whatsapp", "to": to, "type": kind, kind: media},
    ).raise_for_status()


def ask_claude(user: str, text: str, outbox: list) -> str:
    history[user].append({"role": "user", "content": text})
    msgs = list(history[user])
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    answer = ""
    for _ in range(5):  # bucle de herramientas
        resp = client.messages.create(
            model=MODEL, max_tokens=2048, system=SYSTEM, tools=TOOLS, messages=msgs
        )
        answer = "".join(b.text for b in resp.content if b.type == "text")
        if resp.stop_reason != "tool_use":
            break
        msgs.append({"role": "assistant", "content": resp.content})
        msgs.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b.id, "content": run_bridge_tool(b.input, outbox)}
            for b in resp.content if b.type == "tool_use"
        ]})
    history[user].append({"role": "assistant", "content": answer or "(sin respuesta)"})
    return answer or "No pude completar el cálculo, intenta de nuevo."


def valid_signature() -> bool:
    secret = os.environ.get("WHATSAPP_APP_SECRET")
    if not secret:
        return True
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


@app.get("/webhook")
def verify():
    if (
        request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == os.environ.get("WHATSAPP_VERIFY_TOKEN")
    ):
        return request.args.get("hub.challenge", ""), 200
    abort(403)


@app.post("/webhook")
def incoming():
    if not valid_signature():
        abort(403)
    data = request.get_json(silent=True) or {}
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for m in change.get("value", {}).get("messages", []):
                if m["id"] in seen:
                    continue
                seen.append(m["id"])
                if m.get("type") != "text":
                    send(m["from"], "Por ahora solo entiendo mensajes de texto.")
                    continue
                try:
                    outbox = []
                    send(m["from"], ask_claude(m["from"], m["text"]["body"], outbox))
                    for name, data, mime in outbox:
                        send_file(m["from"], name, data, mime)
                except Exception:
                    app.logger.exception("Error procesando mensaje")
                    send(m["from"], "Hubo un error, intenta de nuevo en un momento.")
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
