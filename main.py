import os, asyncio, json, re, time
from datetime import datetime
from telethon import TelegramClient, events
from dotenv import load_dotenv
from predictor import CardPredictor
from yaml_manager import init_database
from card_counter import CardCounter
from aiohttp import web

load_dotenv()

# ---------- CONFIG ----------
API_ID   = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
BOT_TOKEN= os.getenv("BOT_TOKEN") or ""
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
PORT     = int(os.getenv('PORT', 10000))

# ---------- GLOBALS ----------
detected_stat_channel  = None
detected_display_channel = int(os.getenv("DISPLAY_CHANNEL") or 0)
CONFIG_FILE   = "bot_config.json"
INTERVAL_FILE = "interval.json"
AUTO_BILAN_MIN = 30
AUTO_TASK      = None

# File d'attente pour messages en attente
pending_messages = {}  # {message_id: message_text}

database = init_database()
predictor    = CardPredictor()
card_counter = CardCounter()
client       = TelegramClient(f"bot_session_{int(time.time())}", API_ID, API_HASH)

# ---------- CONFIG TOOLS ----------
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

# ---------- AUTO-BILAN ----------
async def auto_bilan_loop():
    while True:
        await asyncio.sleep(AUTO_BILAN_MIN * 60)
        if detected_display_channel:
            msg = card_counter.report_and_reset()  # envoie + reset
            await client.send_message(detected_display_channel, msg)

def restart_auto_bilan():
    global AUTO_TASK
    if AUTO_TASK: AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(auto_bilan_loop())

# ---------- COMMANDS ----------
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
    # Ajouter -100 si manquant pour les canaux Telegram
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
    zip_name = "render_deploy.zip"
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
        for f in ["main.py", "predictor.py", "yaml_manager.py", "card_counter.py", "requirements.txt", ".gitignore"]:
            if os.path.exists(f): z.write(f)
    await e.respond("📦 Package Render créé !")
    await client.send_file(e.chat_id, zip_name, caption="🚀 Prêt pour Render")

@client.on(events.NewMessage(pattern="/dep"))
async def dep_render(e):
    if e.sender_id != ADMIN_ID: return
    import zipfile
    
    zip_name = "de2000.zip"
    
    try:
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
            # main.py - Version modifiée avec PORT=10000 pour Render.com
            main_render_content = open("main.py", "r", encoding="utf-8").read()
            # Remplacer PORT = 5000 par PORT = int(os.getenv("PORT", 10000))
            main_render_content = main_render_content.replace(
                "PORT     = int(os.getenv('PORT', 10000))",
                "PORT     = int(os.getenv('PORT', 10000))"
            )
            z.writestr("main.py", main_render_content)
            
            # Fichiers Python principaux (sauf main.py déjà traité)
            for f in ["predictor.py", "yaml_manager.py", "card_counter.py", "scheduler.py"]:
                if os.path.exists(f):
                    z.write(f)
            
            # Fichiers de configuration
            for f in ["requirements.txt", "runtime.txt", ".gitignore"]:
                if os.path.exists(f):
                    z.write(f)
            
            # Configuration render.yaml pour Render.com
            render_yaml = """services:
  - type: web
    name: telegram-card-counter-bot
    env: python
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
"""
            z.writestr("render.yaml", render_yaml)
            
            # Fichier .env.example pour Render.com
            env_example = """API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_admin_id
DISPLAY_CHANNEL=0
PORT=10000
"""
            z.writestr(".env.example", env_example)
            
            # README de déploiement Render.com
            readme = """# Package de2000 - Déploiement Render.com

## 🚀 Instructions de déploiement sur Render.com:

1. **Créer un compte Render.com**
   - Aller sur https://render.com
   - S'inscrire ou se connecter avec GitHub

2. **Créer un nouveau Web Service**
   - Cliquer sur "New +" → "Web Service"
   - Connecter votre repository GitHub ou uploader le code

3. **Configuration du service**
   - **Name**: telegram-card-counter-bot
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Port**: 10000 (automatique via render.yaml)

4. **Configurer les variables d'environnement**
   Dans l'onglet "Environment", ajouter:
   - `API_ID`: Votre Telegram API ID (my.telegram.org)
   - `API_HASH`: Votre Telegram API Hash
   - `BOT_TOKEN`: Token du bot (@BotFather)
   - `ADMIN_ID`: Votre Telegram User ID
   - `DISPLAY_CHANNEL`: ID du canal d'affichage (optionnel)
   - `PORT`: 10000 (déjà configuré)

5. **Déployer**
   - Cliquer sur "Create Web Service"
   - Le déploiement démarre automatiquement
   - Vérifier les logs pour confirmer la connexion

## 📋 Caractéristiques de2000:
✅ **Port 10000**: Configuration Render.com optimisée
✅ **Base YAML**: Stockage sans PostgreSQL
✅ **Gestion file d'attente**: Messages ⏰ → ✅/🔰
✅ **Comptage unique**: Anti-double comptage avec hash SHA256
✅ **Rapports automatiques**: Intervalle configurable
✅ **Prédictions**: Système de prédictions de cartes
✅ **Health Check**: Endpoint /health pour monitoring

## 🔧 Commandes disponibles:
- `/status` - État complet du système
- `/set_stat [id]` - Configurer canal source
- `/set_display [id]` - Configurer canal affichage
- `/intervalle [min]` - Intervalle rapports (1-120 min)
- `/bilan` - Rapport immédiat et reset
- `/reset` - Réinitialiser compteur
- `/deploy` - Package render_deploy.zip
- `/dep` - Package de2000.zip (Render.com optimisé)

## 📊 Architecture:
- **main.py**: Application principale avec port 10000
- **card_counter.py**: Logique de comptage de cartes
- **predictor.py**: Système de prédictions
- **yaml_manager.py**: Gestion données YAML
- **scheduler.py**: Planification automatique
- **render.yaml**: Configuration déploiement Render.com

## 🌐 Endpoints:
- `GET /health`: Health check (retourne "Bot OK")
- `GET /`: Root endpoint (retourne "Bot OK")

## 🗄️ Stockage YAML:
- `data/bot_config.yaml`: Configuration persistante
- `data/predictions.yaml`: Historique prédictions
- `data/auto_predictions.yaml`: Planification auto
- `data/message_log.yaml`: Anti-doublon messages
- `bot_config.json`: Backup configuration
- `interval.json`: Intervalle rapports

## ⚙️ Fonctionnement:
1. **Messages en attente (⏰)**: Mis en file d'attente
2. **Messages édités**: Détection ⏰ → ✅/🔰
3. **Messages finalisés (✅/🔰)**: Comptage immédiat
4. **Anti-doublon**: Hash SHA256 + YAML log
5. **Rapports**: Instantanés + périodiques configurables

## ⚠️ Important:
- Le dossier `data/` est créé automatiquement
- Les sessions Telegram sont générées au démarrage
- Configuration sauvegardée en YAML + JSON
- Port 10000 OBLIGATOIRE pour Render.com
- Variables d'environnement via dashboard Render.com

## 🚀 Déploiement rapide:
```bash
# 1. Décompresser de2000.zip
unzip de2000.zip

# 2. Upload sur Render.com ou GitHub
git init
git add .
git commit -m "Initial commit"
git push origin main

# 3. Connecter sur Render.com et déployer
# Les variables sont dans .env.example
```

## 📈 Monitoring:
- Logs en temps réel dans dashboard Render.com
- Health check automatique: `https://your-app.onrender.com/health`
- Console output détaillé avec timestamps

🎯 Package de2000 prêt pour déploiement Render.com avec port 10000!
"""
            z.writestr("README_RENDER.md", readme)
        
        await e.respond("📦 Package de2000.zip créé avec succès!\n✅ Optimisé pour Render.com (Port 10000)\n🔧 Tous les fichiers configurés et prêts au déploiement")
        await client.send_file(e.chat_id, zip_name, caption="🚀 Package de2000.zip prêt pour Render.com (Port 10000)")
        
        # Nettoyer le fichier ZIP après envoi
        if os.path.exists(zip_name):
            os.remove(zip_name)
            
    except Exception as ex:
        await e.respond(f"❌ Erreur lors de la création du package: {ex}")

# ---------- MESSAGE HANDLER ----------
@client.on(events.NewMessage())
async def handle_new(e):
    if e.chat_id != detected_stat_channel: return
    txt = e.message.message or ""
    
    # Messages en attente (⏰) → Mise en file d'attente
    if "⏰" in txt or "🕐" in txt:
        pending_messages[e.message.id] = txt
        print(f"⏰ Message mis en attente (ID: {e.message.id}): {txt[:50]}...")
        return
    
    # Messages finalisés (✅ ou 🔰) → Traitement immédiat
    if "✅" in txt or "🔰" in txt:
        await process_finalized_message(txt, e.chat_id)
    else:
        print(f"⏭️ Message non finalisé ignoré : {txt[:50]}...")

@client.on(events.MessageEdited())
async def handle_edited(e):
    if e.chat_id != detected_stat_channel: return
    txt = e.message.message or ""
    
    # Vérifier si le message était en attente
    if e.message.id in pending_messages:
        # Le message a été édité et n'est plus en attente
        if "⏰" not in txt and "🕐" not in txt:
            # Message finalisé (✅ ou 🔰)
            if "✅" in txt or "🔰" in txt:
                print(f"✅ Message finalisé (ID: {e.message.id}): {txt[:50]}...")
                # Retirer de la file d'attente
                del pending_messages[e.message.id]
                # Traiter le message finalisé
                await process_finalized_message(txt, e.chat_id)
            else:
                # Message édité mais pas finalisé
                print(f"⚠️ Message édité mais non finalisé (ID: {e.message.id}): {txt[:50]}...")
                del pending_messages[e.message.id]
        else:
            # Toujours en attente, mettre à jour le texte
            pending_messages[e.message.id] = txt
            print(f"⏰ Message en attente mis à jour (ID: {e.message.id})")

async def process_finalized_message(txt: str, chat_id: int):
    """Traite un message finalisé et compte les cartes"""
    # Vérifier si le message a déjà été traité (évite double comptage)
    if database.is_message_processed(txt, chat_id):
        print(f"⏭️ Message déjà traité, ignoré")
        return

    # Compter les cartes
    card_counter.add(txt)
    print(f"🃏 Cartes comptées : {txt[:50]}...")

    # Marquer comme traité
    database.mark_message_processed(txt, chat_id)

    # ===== ENVOI INSTANTANÉ (sans reset) =====
    instant = card_counter.build_report()
    if detected_display_channel:
        try:
            await client.send_message(detected_display_channel, instant)
            print(f"📈 Instantané envoyé : {instant}")
        except Exception as ex:
            print(f"❌ Erreur envoi instantané : {ex}")

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
    load_config()
    load_interval()
    await create_web()
    await client.start(bot_token=BOT_TOKEN)
    restart_auto_bilan()
    me = await client.get_me()
    print(f"Bot connecté : @{me.username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())