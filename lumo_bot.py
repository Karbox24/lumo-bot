import logging
import os
import json
import random
from io import StringIO
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import firebase_admin
from firebase_admin import credentials, firestore
import difflib

# Inicializar Firebase desde variable de entorno
firebase_json = os.environ.get("FIREBASE_CONFIG")
cred_dict = json.load(StringIO(firebase_json))
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Menú con botones
menu_principal = ReplyKeyboardMarkup(
    [["/reto", "/puntos"], ["/salir"]],
    resize_keyboard=True
)

# Frases emocionales aleatorias
frases_emocionales = [
    "🌱 Qué hermoso lo que compartiste. Tu corazón está floreciendo.",
    "💫 Me alegra que te abras así. Tu voz merece ser escuchada.",
    "🌸 Gracias por confiar. Cada palabra tuya es un paso hacia tu luz.",
    "🌿 Lo que dijiste tiene fuerza y ternura. Estoy contigo.",
    "🕊️ Tu sinceridad es un regalo. Gracias por compartirla.",
    "🔥 Cada paso que das te acerca a tu verdad. Estoy orgulloso de ti."
]

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name

    user_ref = db.collection("usuarios").document(user_id)
    if not user_ref.get().exists:
        user_ref.set({
            "nombre": user_name,
            "puntos": 0,
            "retos": [],
            "esperando_respuesta": False,
            "reto_actual": None
        })

    await update.message.reply_text(
        f"🌸 Hola {user_name}, soy Lumo. Estoy aquí para acompañarte, escucharte y ayudarte a florecer desde dentro.\n\n"
        "¿Quieres comenzar con tu primer reto emocional? Usa el menú o escribe /reto 💫",
        reply_markup=menu_principal
    )

# Comando /reto
async def reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_ref = db.collection("usuarios").document(user_id)
    user_data = user_ref.get().to_dict()

    last_id = user_data.get("reto_actual", 0)
    retos_ref = db.collection("retos").where("id", ">", last_id).order_by("id").limit(1)
    docs = retos_ref.stream()

    reto = None
    for doc in docs:
        reto = doc.to_dict()
        break

    if reto:
        user_ref.update({
            "esperando_respuesta": True,
            "reto_actual": reto["id"]
        })
        await update.message.reply_text(f"🌼 Reto {reto['id']}: {reto['texto']}")
    else:
        await update.message.reply_text("✨ Ya completaste todos los retos disponibles. ¡Pronto habrá más!")

# Comando /salir
async def salir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_ref = db.collection("usuarios").document(user_id)
    user_ref.update({"esperando_respuesta": False})

    await update.message.reply_text(
        "🌙 Has salido del modo reto. Puedes volver cuando quieras con /reto 💫",
        reply_markup=menu_principal
    )

# Comando /puntos
async def puntos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_ref = db.collection("usuarios").document(user_id)
    user_data = user_ref.get().to_dict()

    await update.message.reply_text(
        f"✨ Tienes {user_data['puntos']} puntos acumulados. ¡Sigue creciendo!",
        reply_markup=menu_principal
    )

# Manejo de mensajes espontáneos
async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    mensaje = update.message.text.strip()
    mensaje_lower = mensaje.lower()

    # Corrección de errores comunes
    comandos_validos = ["/start", "/reto", "/puntos", "/salir"]
    sugerencia = difflib.get_close_matches(mensaje_lower, comandos_validos, n=1, cutoff=0.7)
    if sugerencia:
        await update.message.reply_text(f"¿Querías decir {sugerencia[0]}? 🌸 Puedes usar el menú también.")
        return

    # Verificar si está esperando respuesta
    user_ref = db.collection("usuarios").document(user_id)
    user_data = user_ref.get().to_dict()

    if user_data.get("esperando_respuesta"):
        if len(mensaje.split()) < 3:
            await update.message.reply_text("🌱 Tu respuesta es muy breve. ¿Podrías compartir un poco más?")
            return

        if mensaje in user_data["retos"]:
            await update.message.reply_text("🌸 Ya compartiste algo similar antes. ¿Quieres intentar con otra perspectiva?")
            return

        nuevos_puntos = user_data["puntos"] + 10
        nuevos_retos = user_data["retos"] + [mensaje]
        respuesta_emocional = random.choice(frases_emocionales)

        user_ref.update({
            "puntos": nuevos_puntos,
            "retos": nuevos_retos,
            "esperando_respuesta": False
        })

        await update.message.reply_text(
            f"{respuesta_emocional}\n✨ Has ganado +10 puntos. Total acumulado: {nuevos_puntos} puntos.",
            reply_markup=menu_principal
        )
    else:
        await update.message.reply_text(
            "🌸 Estoy aquí para ti. Usa el menú para comenzar un reto o ver tus puntos.",
            reply_markup=menu_principal
        )

# Configurar el bot
app = ApplicationBuilder().token("8449933477:AAEtZ5ouKX_SyitQR-hzQ1yi6Lv1h7my4pc").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reto", reto))
app.add_handler(CommandHandler("puntos", puntos))
app.add_handler(CommandHandler("salir", salir))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))

app.run_polling()
