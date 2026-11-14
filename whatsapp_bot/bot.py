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
import os
from collections import defaultdict, deque

import anthropic
import requests
from flask import Flask, abort, request

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
GRAPH_URL = "https://graph.facebook.com/v21.0/{phone_id}/messages"
SYSTEM = (
    "Eres un asistente por WhatsApp para ingeniería de puentes colgantes "
    "(catenaria, parábola, flecha, tensiones, holgura). Responde en español, "
    "breve y claro, sin formato markdown complejo."
)

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


def ask_claude(user: str, text: str) -> str:
    history[user].append({"role": "user", "content": text})
    msgs = list(history[user])
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    resp = client.messages.create(
        model=MODEL, max_tokens=1024, system=SYSTEM, messages=msgs
    )
    answer = "".join(b.text for b in resp.content if b.type == "text")
    history[user].append({"role": "assistant", "content": answer})
    return answer


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
                    send(m["from"], ask_claude(m["from"], m["text"]["body"]))
                except Exception:
                    app.logger.exception("Error procesando mensaje")
                    send(m["from"], "Hubo un error, intenta de nuevo en un momento.")
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
