# puente-colgante

## Bot de WhatsApp con Claude

Código en `whatsapp_bot/`. Webhook Flask que recibe mensajes de la WhatsApp Cloud API (Meta) y responde con Claude.

1. En [developers.facebook.com](https://developers.facebook.com) crea una app con el producto WhatsApp y anota el token, el *Phone number ID* y el *App secret*.
2. Instala y configura:
   ```bash
   pip install -r whatsapp_bot/requirements.txt
   export ANTHROPIC_API_KEY=... WHATSAPP_TOKEN=... WHATSAPP_PHONE_ID=... \
          WHATSAPP_VERIFY_TOKEN=cualquier-texto WHATSAPP_APP_SECRET=...
   gunicorn -b 0.0.0.0:8000 whatsapp_bot.bot:app
   ```
3. Expón el puerto con una URL HTTPS pública (ngrok, Cloud Run, etc.).
4. En Meta, configura el webhook en `https://TU-URL/webhook` con tu `WHATSAPP_VERIFY_TOKEN` y suscríbete al campo `messages`.
