import os, asyncio, json, re, time
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from dotenv import load_dotenv
from predictor import CardPredictor
from yaml_manager import init_database
from card_counter import CardCounter
from scheduler import PredictionScheduler
from aiohttp import web
import config  # Importer la configuration centralisée

load_dotenv()

# ---------- CONFIG ----------
API_ID   = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
BOT_TOKEN= os.getenv("BOT_TOKEN") or ""
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
PORT     = int(os.getenv('PORT', 10000))

# ---------- GLOBALS ----------
# Utiliser la configuration pré-définie dans config.py
detected_stat_channel  = config.STAT_CHANNEL_ID
detected_display_channel = config.DISPLAY_CHANNEL_ID

CONFIG_FILE   = "bot_config.json"
INTERVAL_FILE = "interval.json"
AUTO_BILAN_MIN = 60
AUTO_TASK      = None
SCHEDULER_TASK = None

# Variable requise par scheduler.py pour gérer le cooldown
last_rule_check = datetime.now()

# File d'attente pour messages en attente
pending_messages = {}  # {message_id: message_text}

database = init_database()
predictor    = CardPredictor()
card_counter = CardCounter()
client       = TelegramClient(f"bot_session_{int(time.time())}", API_ID, API_HASH)

# Instance globale du planificateur
scheduler_service = None

# ---------- CONFIG TOOLS ----------
def load_config():
    global detected_stat_channel, detected_display_channel
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            c = json.load(f)
            detected_stat_channel  = c.get("stat_channel", config.STAT_CHANNEL_ID)
            detected_display_channel = c.get("display_channel", config.DISPLAY_CHANNEL_ID)

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"stat_channel": detected_stat_channel, "display_channel": detected_display_channel}, f)

def load_interval():
    global AUTO_BILAN_MIN
    if os.path.exists(INTERVAL_FILE):
        with open(INTERVAL_FILE) as f:
            AUTO_BILAN_MIN = max(1, min(int(json.load(f)), 120))

def save_interval(mins: int):
    with open(INTERVAL_FILE, "w") as f:
        json.dump(mins, f)

# ---------- AUTO-BILAN (Compteur de Cartes) ----------
async def auto_bilan_loop():
    while True:
        # Calculer le temps jusqu'à la prochaine heure pile (minutes 00)
        now = datetime.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        sleep_seconds = (next_hour - now).total_seconds()

        await asyncio.sleep(sleep_seconds)
        if detected_display_channel:
            msg = card_counter.report_and_reset()  # envoie + reset
            try:
                await client.send_message(detected_display_channel, msg)
                print(f"📊 Bilan horaire envoyé à {next_hour.strftime('%H:%M')}")
            except Exception as ex:
                print(f"❌ Erreur envoi bilan horaire: {ex}")

def restart_auto_bilan():
    global AUTO_TASK
    if AUTO_TASK: AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(auto_bilan_loop())

# ---------- COMMANDS ----------
@client.on(events.NewMessage(pattern="/start"))
async def start(e):
    await e.respond("🎯 Bot **Compteur & Planificateur** prêt !\nDéveloppé par Sossou Kouamé Appolinaire")

@client.on(events.NewMessage(pattern="/status"))
async def status(e):
    if e.sender_id != ADMIN_ID: return
    load_config()
    scheduler_status = "Inactif"
    if scheduler_service and scheduler_service.is_running:
        s_stats = scheduler_service.get_schedule_status()
        scheduler_status = f"Actif ({s_stats.get('pending', 0)} en attente, {s_stats.get('launched', 0)} lancés)"
    
    await e.respond(
        f"📡 Canal Source : {detected_stat_channel}\n"
        f"📢 Canal Affichage : {detected_display_channel}\n"
        f"⏱️ Intervalle Bilan : {AUTO_BILAN_MIN} min\n"
        f"📅 Planificateur : {scheduler_status}"
    )

@client.on(events.NewMessage(pattern=r"/set_stat (-?\d+)"))
async def set_stat(e):
    if e.sender_id != ADMIN_ID: return
    global detected_stat_channel
    detected_stat_channel = int(e.pattern_match.group(1))
    save_config()
    # Mettre à jour le planificateur
    if scheduler_service:
        scheduler_service.source_channel_id = detected_stat_channel
    await e.respond("✅ Canal statistiques enregistré.")

@client.on(events.NewMessage(pattern=r"/set_display (-?\d+)"))
async def set_display(e):
    if e.sender_id != ADMIN_ID: return
    global detected_display_channel
    channel_id = int(e.pattern_match.group(1))
    if channel_id > 0 and channel_id > 1000000000:
        channel_id = -1000000000000 - channel_id
    detected_display_channel = channel_id
    save_config()
    # Mettre à jour le planificateur
    if scheduler_service:
        scheduler_service.target_channel_id = detected_display_channel
    await e.respond(f"✅ Canal d'affichage enregistré : {channel_id}")

@client.on(events.NewMessage(pattern="/bilan"))
async def bilan(e):
    if e.sender_id != ADMIN_ID: return
    msg = card_counter.report_and_reset()
    await e.respond(msg)

@client.on(events.NewMessage(pattern="/reset"))
async def reset(e):
    if e.sender_id != ADMIN_ID: return
    card_counter.reset()
    predictor.reset()
    if scheduler_service:
        scheduler_service.regenerate_schedule()
    await e.respond("✅ Tous les compteurs et planifications ont été réinitialisés.")

@client.on(events.NewMessage(pattern="/scheduler_info"))
async def scheduler_info(e):
    if e.sender_id != ADMIN_ID: return
    if not scheduler_service:
        await e.respond("⚠️ Planificateur non initialisé.")
        return
    
    stats = scheduler_service.get_schedule_status()
    msg = (
        f"📅 **État du Planificateur**\n"
        f"Running: {stats['is_running']}\n"
        f"Total prévu: {stats['total']}\n"
        f"Lancés: {stats['launched']}\n"
        f"Vérifiés: {stats['verified']}\n"
        f"En attente: {stats['pending']}\n"
        f"Prochain lancement: {stats['next_launch'] or 'Aucun'}"
    )
    await e.respond(msg)

# ---------- MESSAGE HANDLER ----------
@client.on(events.NewMessage())
async def handle_new(e):
    if e.chat_id != detected_stat_channel: return
    txt = e.message.message or ""

    # 1. Gestion messages en attente (⏰)
    if "⏰" in txt or "🕐" in txt:
        pending_messages[e.message.id] = txt
        print(f"⏰ Message mis en attente (ID: {e.message.id})")
        return

    # 2. Gestion messages finalisés (✅ ou 🔰)
    if "✅" in txt or "🔰" in txt:
        await process_finalized_message(txt, e.chat_id)

@client.on(events.MessageEdited())
async def handle_edited(e):
    if e.chat_id != detected_stat_channel: return
    txt = e.message.message or ""

    if e.message.id in pending_messages:
        if "⏰" not in txt and "🕐" not in txt:
            if "✅" in txt or "🔰" in txt:
                print(f"✅ Message finalisé après édition (ID: {e.message.id})")
                del pending_messages[e.message.id]
                await process_finalized_message(txt, e.chat_id)
            else:
                del pending_messages[e.message.id]
        else:
            pending_messages[e.message.id] = txt

async def process_finalized_message(txt: str, chat_id: int):
    """Traite un message finalisé : Comptage + Vérification Prédictions"""
    
    # A. COMPTEUR DE CARTES (Legacy)
    if not database.is_message_processed(txt, chat_id):
        card_counter.add(txt)
        database.mark_message_processed(txt, chat_id)
        
        # Envoi instantané pour le compteur
        instant = card_counter.build_report()
        if detected_display_channel:
            try:
                # On ne spamme pas le log si ça échoue, c'est moins critique que la prédiction
                await client.send_message(int(detected_display_channel), instant)
            except:
                pass

    # B. VÉRIFICATION DES PRÉDICTIONS (Scheduler)
    # Intégration de la logique fournie dans scheduler.py
    if scheduler_service and scheduler_service.is_running:
        # 1. Récupérer les prédictions lancées mais non vérifiées
        to_verify = scheduler_service.get_predictions_to_verify()
        
        if to_verify:
            # Extraire la liste des numéros prédits (format int)
            predicted_numbers = []
            for n_str, _ in to_verify:
                try:
                    predicted_numbers.append(int(n_str.replace('N', '')))
                except ValueError:
                    pass
            
            # 2. Vérifier si le message correspond à une prédiction
            # Utilise la méthode verify_prediction_from_message de scheduler.py
            matched_num, status = scheduler_service.verify_prediction_from_message(txt, predicted_numbers)
            
            if matched_num:
                # Trouver la clé correspondante (ex: N0730)
                numero_key = None
                prediction_data = None
                
                for n_key, data in to_verify:
                    if int(n_key.replace('N', '')) == matched_num:
                        numero_key = n_key
                        prediction_data = data
                        break
                
                # 3. Mettre à jour le message de prédiction
                if numero_key and prediction_data:
                    prediction_data["verified"] = True
                    prediction_data["statut"] = status
                    
                    # Mettre à jour le message sur Telegram (ex: 🔵Num 🔵2D: statut :✅1️⃣)
                    await scheduler_service.update_prediction_message(numero_key, prediction_data, status)
                    
                    # Sauvegarder l'état
                    scheduler_service.save_schedule(scheduler_service.schedule_data)
                    print(f"🏁 Prédiction {numero_key} clôturée avec statut {status}")

# ---------- WEB SERVER ----------
async def health(request): return web.Response(text="Bot OK")
async def create_web():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Web server on 0.0.0.0:{PORT}")
    return runner

# ---------- START ----------
async def main():
    global detected_display_channel, scheduler_service, SCHEDULER_TASK
    
    load_config()
    load_interval()
    
    # 1. Démarrer Serveur Web
    await create_web()
    
    # 2. Démarrer Telegram Client
    await client.start(bot_token=BOT_TOKEN)

    # Vérifier accès canal affichage
    if detected_display_channel:
        try:
            entity = await client.get_entity(int(detected_display_channel))
            print(f"✅ Canal d'affichage connecté : {entity.title} (ID: {detected_display_channel})")
        except Exception as ex:
            print(f"⚠️ Erreur accès canal affichage : {ex}")

    # 3. Démarrer Tâches de fond
    restart_auto_bilan()
    
    # 4. Initialiser et Démarrer le Planificateur (Scheduler)
    if detected_stat_channel and detected_display_channel:
        scheduler_service = PredictionScheduler(
            client, 
            predictor, 
            int(detected_stat_channel), 
            int(detected_display_channel)
        )
        SCHEDULER_TASK = asyncio.create_task(scheduler_service.run_scheduler())
        print("🚀 Service Planificateur initialisé")
    else:
        print("⚠️ Planificateur non démarré : Canaux non configurés")

    me = await client.get_me()
    print(f"🤖 Bot connecté : @{me.username}")
    
    # Boucle principale
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
