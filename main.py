import os, asyncio, json, re, time
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from dotenv import load_dotenv
from predictor import CardPredictor
from yaml_manager import init_database
from card_counter import CardCounter
from aiohttp import web
import config

load_dotenv()

API_ID   = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
BOT_TOKEN= os.getenv("BOT_TOKEN") or ""
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
PORT     = int(os.getenv('PORT', 5000))

detected_stat_channel  = config.STAT_CHANNEL_ID
detected_display_channel = config.DISPLAY_CHANNEL_ID
CONFIG_FILE   = "bot_config.json"
INTERVAL_FILE = "interval.json"
AUTO_BILAN_MIN = 30
AUTO_TASK      = None

pending_messages = {}
database = init_database()
predictor    = CardPredictor()
card_counter = CardCounter()
client       = TelegramClient(f"bot_session_{int(time.time())}", API_ID, API_HASH)

def load_config():
    global detected_stat_channel, detected_display_channel
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            c = json.load(f)
            detected_stat_channel  = c.get("stat_channel")
            detected_display_channel = c.get("display_channel", detected_display_channel)

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

async def auto_bilan_loop():
    while True:
        now = datetime.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        sleep_seconds = (next_hour - now).total_seconds()
        await asyncio.sleep(sleep_seconds)
        if detected_display_channel:
            msg = card_counter.report_and_reset()
            await client.send_message(detected_display_channel, msg)
            print(f"📊 Bilan horaire envoyé à {next_hour.strftime('%H:%M')}")

def restart_auto_bilan():
    global AUTO_TASK
    if AUTO_TASK: AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(auto_bilan_loop())

@client.on(events.NewMessage(pattern="/start"))
async def start(e):
    await e.respond("🎯 Bot **Compteur de cartes** prêt !\nDéveloppé par Sossou Kouamé Appolinaire")

@client.on(events.NewMessage(pattern="/status"))
async def status(e):
    if e.sender_id != ADMIN_ID: return
    load_config()
    await e.respond(f"Stat canal : {detected_stat_channel}\nAffichage canal : {detected_display_channel}\nIntervalle : {AUTO_BILAN_MIN} min")

@client.on(events.NewMessage(pattern=r"/set_stat (-?\d+)"))
async def set_stat(e):
    if e.sender_id != ADMIN_ID or e.is_group: return
    global detected_stat_channel
    detected_stat_channel = int(e.pattern_match.group(1))
    save_config()
    await e.respond("✅ Canal statistiques enregistré.")

@client.on(events.NewMessage(pattern=r"/set_display (-?\d+)"))
async def set_display(e):
    if e.sender_id != ADMIN_ID or e.is_group: return
    global detected_display_channel
    channel_id = int(e.pattern_match.group(1))
    if channel_id > 0 and channel_id > 1000000000:
        channel_id = -1000000000000 - channel_id
    detected_display_channel = channel_id
    save_config()
    await e.respond(f"✅ Canal d'affichage enregistré : {channel_id}")

@client.on(events.NewMessage(pattern=r"/intervalle"))
async def set_interval(e):
    if e.sender_id != ADMIN_ID: return
    try:
        mins = int(e.message.message.split()[1])
        mins = max(1, min(mins, 120))
    except (ValueError, IndexError):
        await e.respond("Usage : `/intervalle 5` (1-120 min)")
        return
    save_interval(mins)
    global AUTO_BILAN_MIN
    AUTO_BILAN_MIN = mins
    restart_auto_bilan()
    await e.respond(f"✅ Bilan automatique toutes les {mins} min")

@client.on(events.NewMessage(pattern="/bilan"))
async def bilan(e):
    if e.sender_id != ADMIN_ID: return
    msg = card_counter.report_and_reset()
    await e.respond(msg)

@client.on(events.NewMessage(pattern="/reset"))
async def reset(e):
    if e.sender_id != ADMIN_ID: return
    card_counter.reset()
    await e.respond("✅ Compteur remis à zéro.")

@client.on(events.NewMessage(pattern="/deploy"))
async def deploy(e):
    if e.sender_id != ADMIN_ID: return
    import zipfile
    zip_name = "joueu2.zip"
    try:
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
            main_render_content = open("main.py", "r", encoding="utf-8").read()
            main_render_content = main_render_content.replace(
                "PORT     = int(os.getenv('PORT', 10000'))",
                "PORT     = int(os.getenv('PORT', 10000'))"
            )
            z.writestr("main.py", main_render_content)
            for f in ["predictor.py", "yaml_manager.py", "card_counter.py", "scheduler.py", "config.py"]:
                if os.path.exists(f):
                    z.write(f)
            z.writestr("runtime.txt", "python-3.11.10")
            z.writestr("requirements.txt", """telethon==1.35.0
aiohttp==3.9.5
PyYAML==6.0.1
python-dotenv==1.0.1
""")
            z.writestr("render.yaml", """services:
  - type: web
    name: telegram-card-counter-bot
    env: python
    runtime: python-3.11.10
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: PORT
        value: 10000
      - key: API_ID
        sync: false
      - key: API_HASH
        sync: false
      - key: BOT_TOKEN
        sync: false
      - key: ADMIN_ID
        sync: false
      - key: DISPLAY_CHANNEL
        sync: false
""")
            z.writestr(".env.example", """API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_admin_id
DISPLAY_CHANNEL=-1003216148681
PORT=10000
""")
            z.writestr(".gitignore", """*.session
*.session-journal
.env
__pycache__/
*.py[cod]
*.json
*.yaml
*.yml
.vscode/
.idea/
*.log
.DS_Store
Thumbs.db
""")
            z.writestr("README.md", "README complet ici")
        await e.respond("📦 joueu2.zip créé avec succès!")
        await client.send_file(e.chat_id, zip_name, caption="🚀 joueu2.zip - Déploiement complet")
    except Exception as ex:
        await e.respond(f"❌ Erreur: {ex}")

@client.on(events.NewMessage(pattern="/dep"))
async def dep_render(e):
    if e.sender_id != ADMIN_ID: return
    import zipfile
    zip_name = "render10k.zip"
    try:
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
            main_render_content = open("main.py", "r", encoding="utf-8").read()
            main_render_content = main_render_content.replace(
                "PORT     = int(os.getenv('PORT', 10000'))",
                "PORT     = int(os.getenv('PORT', 10000'))"
            )
            z.writestr("main.py", main_render_content)
            for f in ["predictor.py", "yaml_manager.py", "card_counter.py", "scheduler.py"]:
                if os.path.exists(f):
                    z.write(f)
            z.writestr("runtime.txt", "python-3.11.10")
            z.writestr("requirements.txt", """telethon==1.35.0
aiohttp==3.9.5
PyYAML==6.0.1
python-dotenv==1.0.1
""")
            z.writestr("render.yaml", """services:
  - type: web
    name: telegram-card-counter-bot
    env: python
    runtime: python-3.11.10
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: PORT
        value: 10000
      - key: API_ID
        sync: false
      - key: API_HASH
        sync: false
      - key: BOT_TOKEN
        sync: false
      - key: ADMIN_ID
        sync: false
      - key: DISPLAY_CHANNEL
        sync: false
""")
            z.writestr(".env.example", """API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_admin_id
DISPLAY_CHANNEL=0
PORT=10000
""")
            z.writestr("README_RENDER.md", "README complet ici")
        await e.respond("📦 render10k.zip créé avec succès!")
        await client.send_file(e.chat_id, zip_name, caption="🚀 render10k.zip - Render.com (Python 3.11 + Port 10000)")
    except Exception as ex:
        await e.respond(f"❌ Erreur: {ex}")

@client.on(events.NewMessage())
async def handle_new(e):
    if e.chat_id != detected_stat_channel: return
    txt = e.message.message or ""
    if "⏰" in txt or "🕐" in txt:
        pending_messages[e.message.id] = txt
        print(f"⏰ Message mis en attente (ID: {e.message.id}): {txt[:50]}...")
        return
    if "✅" in txt or "🔰" in txt:
        await process_finalized_message(txt, e.chat_id)
    else:
        print(f"⏭️ Message non finalisé ignoré : {txt[:50]}...")

@client.on(events.MessageEdited())
async def handle_edited(e):
    if e.chat_id != detected_stat_channel: return
    txt = e.message.message or ""
    if e.message.id in pending_messages:
        if "⏰" not in txt and "🕐" not in txt:
            if "✅" in txt or "🔰" in txt:
                print(f"✅ Message finalisé (ID: {e.message.id}): {txt[:50]}...")
                del pending_messages[e.message.id]
                await process_finalized_message(txt, e.chat_id)
            else:
                print(f"⚠️ Message édité mais non finalisé (ID: {e.message.id}): {txt[:50]}...")
                del pending_messages[e.message.id]
        else:
            pending_messages[e.message.id] = txt
            print(f"⏰ Message en attente mis à jour (ID: {e.message.id})")

async def process_finalized_message(txt: str, chat_id: int):
    if database.is_message_processed(txt, chat_id):
        print(f"⏭️ Message déjà traité, ignoré")
        return
    card_counter.add(txt)
    database.mark_message_processed(txt, chat_id)
    instant = card_counter.build_report()
    if detected_display_channel:
        try:
            await client.send_message(int(detected_display_channel), instant)
            print(f"📈 Instantané envoyé au canal : {instant}")
        except Exception as ex:
            print(f"❌ Erreur envoi instantané : {ex}")
            try:
                await client.get_entity(int(detected_display_channel))
                await client.send_message(detected_display_channel, instant)
                print(f"✅ Instantané envoyé (via entité) : {instant}")
            except Exception as ex2:
                print(f"❌ Échec total envoi : {ex2}")

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

async def main():
    global detected_display_channel
    load_config()
    load_interval()
    await create_web()
    await client.start(bot_token=BOT_TOKEN)
    if detected_display_channel:
        try:
            entity = await client.get_entity(int(detected_display_channel))
            print(f"✅ Canal d'affichage trouvé : {entity.title} (ID: {detected_display_channel})")
        except Exception as ex:
            print(f"⚠️ Impossible d'accéder au canal d'affichage {detected_display_channel}: {ex}")
    restart_auto_bilan()
    me = await client.get_me()
    print(f"Bot connecté : @{me.username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

