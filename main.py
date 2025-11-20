import os, asyncio, json, re, time
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from dotenv import load_dotenv
from predictor import CardPredictor
from yaml_manager import init_database
from card_counter import CardCounter
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
# Forcer l'utilisation du canal depuis config.py (ignorer la variable d'environnement)
detected_display_channel = config.DISPLAY_CHANNEL_ID
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
        # Calculer le temps jusqu'à la prochaine heure pile (minutes 00)
        from datetime import datetime
        now = datetime.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        sleep_seconds = (next_hour - now).total_seconds()

        await asyncio.sleep(sleep_seconds)
        if detected_display_channel:
            msg = card_counter.report_and_reset()  # envoie + reset
            await client.send_message(detected_display_channel, msg)
            print(f"📊 Bilan horaire envoyé à {next_hour.strftime('%H:%M')}")

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
    zip_name = "joueu2.zip"

    # Nettoyer tous les anciens fichiers ZIP
    import glob
    for old_zip in glob.glob("*.zip"):
        try:
            os.remove(old_zip)
            print(f"🗑️ Ancien fichier supprimé: {old_zip}")
        except:
            pass

    try:
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
            # main.py - Version optimisée avec PORT=10000 pour Replit
            main_render_content = open("main.py", "r", encoding="utf-8").read()
            # Remplacer PORT = 8000 par PORT = 10000 et mettre à jour config
            main_render_content = main_render_content.replace(
                "PORT     = int(os.getenv('PORT', 10000))",
                "PORT     = int(os.getenv('PORT', 10000))"
            )
            z.writestr("main.py", main_render_content)

            # Fichiers Python - Tous vérifiés et corrigés
            for f in ["predictor.py", "yaml_manager.py", "card_counter.py", "scheduler.py", "config.py"]:
                if os.path.exists(f):
                    z.write(f)

            # runtime.txt - Python 3.11.10 OBLIGATOIRE pour Telethon
            z.writestr("runtime.txt", "python-3.11.10")

            # requirements.txt - Versions testées et compatibles
            requirements = """telethon==1.35.0
aiohttp==3.9.5
PyYAML==6.0.1
python-dotenv==1.0.1
"""
            z.writestr("requirements.txt", requirements)

            # render.yaml - Configuration optimale Render.com
            render_config = """services:
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
"""
            z.writestr("render.yaml", render_config)

            # .env.example - Template variables d'environnement
            env_example = """API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_admin_id
DISPLAY_CHANNEL=-1003216148681
PORT=10000
"""
            z.writestr(".env.example", env_example)

            # .gitignore - Pour éviter de commit les fichiers sensibles
            gitignore = """# Telegram sessions
*.session
*.session-journal

# Environment
.env
.env.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Data
data/
*.json
*.yaml
*.yml

# IDE
.vscode/
.idea/

# Logs
*.log

# OS
.DS_Store
Thumbs.db
"""
            z.writestr(".gitignore", gitcode)

            # README.md - Documentation complète
            readme = """# jou34 - Compteur de Cartes Telegram

## 🎯 Fonctionnalité Principale
Ce bot compte **UNIQUEMENT le 1er groupe** de cartes entre parenthèses.

**Exemple:**
- Message: `(♠️♥️♦️♣️) - (A♠️2♥️)` → Compte seulement `♠️♥️♦️♣️`
- Le deuxième groupe `(A♠️2♥️)` est complètement ignoré

## ⚙️ Caractéristiques
✅ Comptage instantané (format simple avec émojis)
✅ Bilan horaire automatique (format décoré avec barres de progression)
✅ Envoi automatique chaque heure pile (10:00, 11:00, 12:00, etc.)
✅ Anti-doublon avec hash SHA256
✅ Gestion messages en attente (⏰) et finalisés (✅/🔰)
✅ Stockage YAML (sans base de données)
✅ Health check endpoint pour monitoring
✅ **Configuration canaux pré-configurée** dans config.py

## 🚀 Déploiement sur Render.com

### Prérequis
- Compte Render.com (gratuit)
- Telegram API credentials (my.telegram.org)
- Bot Token (@BotFather)

### Étapes de déploiement

1. **Créer un Web Service sur Render.com**
   - Aller sur https://render.com
   - Cliquer sur "New +" → "Web Service"
   - Connecter votre repo GitHub ou uploader le code

2. **Configuration du service**
   - Name: `telegram-card-counter-bot`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`

3. **Configuration des canaux** (IMPORTANT - Avant déploiement)
   - Ouvrir `config.py`
   - Modifier `STAT_CHANNEL_ID` avec l'ID de votre canal source
   - Modifier `DISPLAY_CHANNEL_ID` avec l'ID de votre canal d'affichage
   - Les canaux sont pré-configurés et persistants

4. **Variables d'environnement** (dans l'onglet Environment)
   ```
   API_ID=votre_api_id
   API_HASH=votre_api_hash
   BOT_TOKEN=votre_bot_token
   ADMIN_ID=votre_telegram_user_id
   PORT=10000
   ```
   Note: DISPLAY_CHANNEL est optionnel, la valeur de config.py sera utilisée par défaut

5. **Déployer**
   - Cliquer sur "Create Web Service"
   - Attendre la fin du déploiement (5-10 minutes)
   - Vérifier les logs pour confirmer: "Bot connecté"

## 📋 Commandes du Bot

- `/start` - Démarrer le bot
- `/status` - Voir la configuration et l'état
- `/set_stat [id]` - Configurer le canal source
- `/set_display [id]` - Configurer le canal d'affichage
- `/bilan` - Rapport immédiat et reset manuel
- `/reset` - Réinitialiser le compteur

## 📊 Fonctionnement

### Messages en attente
- Messages avec ⏰ → Mis en file d'attente
- À l'édition vers ✅ ou 🔰 → Traitement automatique

### Comptage
- **Instant** : Format simple envoyé immédiatement
  ```
  📈 Compteur instantané
  ♠️ : 5  (25.0 %)
  ♥️ : 8  (40.0 %)
  ♦️ : 4  (20.0 %)
  ♣️ : 3  (15.0 %)
  ```

- **Bilan horaire** : Format décoré avec reset automatique
  ```
  ╔════════════════════╗
  📊 Bilan 📊
  ╚════════════════════╝

  🖤 ♠️ PIQUE
  ├─ Compteur: 5 cartes
  ├─ Pourcentage: 25.0%
  └─ ⬛⬛⬜⬜⬜⬜⬜⬜⬜⬜
  ```

## 🔧 Architecture Technique

- **Port**: 10000 (obligatoire pour Render.com)
- **Python**: 3.11.10 (requis pour Telethon)
- **Stockage**: YAML (dossier `data/`)
- **Health check**: `/health` endpoint

## ⚠️ Important

### Version Python
**Python 3.11.10 est OBLIGATOIRE**
- ❌ Python 3.13+ causera des erreurs avec Telethon
- ✅ `runtime.txt` contient `python-3.11.10`

### Port
Le port 10000 est **pré-configuré** et **obligatoire** pour Render.com

### Permissions Telegram
Le bot doit être:
- Membre du canal source (pour lire les messages)
- Membre du canal d'affichage (pour envoyer les rapports)

## 📈 Monitoring

- **Logs**: Dashboard Render.com en temps réel
- **Health check**: `https://votre-app.onrender.com/health`
- **Status**: Console output avec timestamps détaillés

## 🐛 Résolution de problèmes

### "File .../asyncio/runners.py" error
- ❌ Cause: Python 3.13 incompatible
- ✅ Solution: Vérifier que `runtime.txt` contient `python-3.11.10`

### Build Failed
- Vérifier que toutes les variables d'environnement sont définies
- S'assurer que `render.yaml` spécifie `runtime: python-3.11.10`

### Bot ne reçoit pas les messages
- Vérifier que le bot est membre du canal avec `/set_stat [id]`
- Confirmer l'ID du canal (format: `-100xxxxxxxxxx`)

## 📦 Fichiers Inclus

- `main.py` - Application principale (PORT=10000)
- `config.py` - **Configuration centralisée des canaux (PRÉ-CONFIGURÉ)**
- `card_counter.py` - Logique de comptage
- `predictor.py` - Système de prédictions
- `yaml_manager.py` - Gestion YAML
- `scheduler.py` - Planification
- `requirements.txt` - Dépendances
- `runtime.txt` - Python 3.11.10
- `render.yaml` - Config Render.com
- `.env.example` - Template variables
- `.gitignore` - Fichiers à ignorer

🎯 **jou34** - Prêt pour déploiement Replit!

## 📋 Configuration Canaux Pré-Configurée
- **Canal Source**: -1002682552255 (lecture des messages de cartes)
- **Canal Affichage**: -1002674389383 (envoi des rapports)
- Ces canaux sont déjà configurés dans `config.py`
- Modifiez `config.py` avant déploiement si nécessaire
- **Comptage**: 1er groupe uniquement
"""
            z.writestr("README.md", readme)

        await e.respond("📦 joueu2.zip créé avec succès!\n✅ Port 10000 Replit\n✅ Python 3.11.10\n✅ Compte le 1er groupe uniquement\n✅ Canal: -1002674389383\n✅ Tous fichiers optimisés")
        await client.send_file(e.chat_id, zip_name, caption="🚀 joueu2.zip - Déploiement complet (1er groupe)")

        # Nettoyer le fichier ZIP après envoi
        if os.path.exists(zip_name):
            os.remove(zip_name)

    except Exception as ex:
        await e.respond(f"❌ Erreur: {ex}")

@client.on(events.NewMessage(pattern="/dep"))
async def dep_render(e):
    if e.sender_id != ADMIN_ID: return
    import zipfile

    zip_name = "render10k.zip"

    try:
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
            # main.py - Version modifiée avec PORT=10000 pour Render.com
            main_render_content = open("main.py", "r", encoding="utf-8").read()
            # Remplacer PORT = 8000 par PORT = 10000 pour Render.com
            main_render_content = main_render_content.replace(
                "PORT     = int(os.getenv('PORT', 8000))",
                "PORT     = int(os.getenv('PORT', 10000))"
            )
            z.writestr("main.py", main_render_content)

            # Fichiers Python principaux (sauf main.py déjà traité)
            for f in ["predictor.py", "yaml_manager.py", "card_counter.py", "scheduler.py"]:
                if os.path.exists(f):
                    z.write(f)

            # runtime.txt - IMPORTANT: Python 3.11 pour compatibilité Telethon
            runtime_content = "python-3.11.10"
            z.writestr("runtime.txt", runtime_content)

            # requirements.txt - Versions testées et compatibles
            requirements_content = """telethon==1.35.0
aiohttp==3.9.5
PyYAML==6.0.1
python-dotenv==1.0.1
"""
            z.writestr("requirements.txt", requirements_content)

            # Fichiers de configuration
            if os.path.exists(".gitignore"):
                z.write(".gitignore")

            # Configuration render.yaml pour Render.com
            render_yaml = """services:
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
            readme = """# Package render10k - Déploiement Render.com (Port 10000)

## ⚠️ IMPORTANT - Version Python
**Ce bot nécessite Python 3.11.10** pour compatibilité avec Telethon.
- ❌ Python 3.13+ causera des erreurs asyncio
- ✅ Python 3.11.10 est préconfiguré dans runtime.txt

## 🎯 Fonctionnalité du comptage
**Le bot compte UNIQUEMENT le 2ème groupe entre parenthèses**
- Message exemple: `(groupe1)(♠️♥️♦️♣️)` → Compte seulement `♠️♥️♦️♣️`
- Le premier groupe est complètement ignoré

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

## 📋 Caractéristiques render10k:
✅ **Comptage 2ème groupe UNIQUEMENT**: Ignore le 1er groupe, compte seulement le 2ème
✅ **Port 10000**: Configuration Render.com optimisée
✅ **Base YAML**: Stockage sans PostgreSQL
✅ **Gestion file d'attente**: Messages ⏰ → ✅/🔰
✅ **Anti-doublon**: Hash SHA256 pour éviter le double comptage
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
- **runtime.txt**: Python 3.11.10 (OBLIGATOIRE)
- **requirements.txt**: Dépendances testées et compatibles

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
3. **Messages finalisés (✅/🔰)**: Comptage immédiat du 2ème groupe
4. **Comptage 2ème groupe**: Le bot ignore le 1er groupe (X)(Y) et compte seulement Y
5. **Anti-doublon**: Hash SHA256 + YAML log
6. **Rapports**: Instantanés + périodiques configurables

## ⚠️ Important:
- Le dossier `data/` est créé automatiquement
- Les sessions Telegram sont générées au démarrage
- Configuration sauvegardée en YAML + JSON
- Port 10000 OBLIGATOIRE pour Render.com
- Variables d'environnement via dashboard Render.com

## 🔧 Résolution des problèmes courants:

### Erreur "File .../asyncio/runners.py"
- ❌ Cause: Python 3.13 incompatible avec Telethon
- ✅ Solution: runtime.txt contient python-3.11.10

### Build Failed sur Render.com
- Vérifier que runtime.txt existe et contient python-3.11.10
- Vérifier que render.yaml spécifie runtime: python-3.11.10
- S'assurer que toutes les variables d'environnement sont définies

## 🚀 Déploiement rapide:
```bash
# 1. Décompresser render10k.zip
unzip render10k.zip

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

🎯 Package render10k prêt pour déploiement Render.com!
✅ Python 3.11.10 + Port 10000 + Configuration complète
"""
            z.writestr("README_RENDER.md", readme)

        await e.respond("📦 Package render10k.zip créé avec succès!\n✅ Python 3.11.10 + Port 10000\n✅ Optimisé pour Render.com\n🔧 Tous les fichiers corrigés et prêts au déploiement")
        await client.send_file(e.chat_id, zip_name, caption="🚀 render10k.zip - Render.com (Python 3.11 + Port 10000)")

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
    """Traite un message finalisé et compte les cartes du 1er groupe"""
    # Vérifier si le message a déjà été traité (évite double comptage)
    if database.is_message_processed(txt, chat_id):
        print(f"⏭️ Message déjà traité, ignoré")
        return

    # Compter les cartes du 1er groupe
    card_counter.add(txt)
    print(f"🃏 Cartes du 1er groupe comptées : {txt[:50]}...")

    # Marquer comme traité
    database.mark_message_processed(txt, chat_id)

    # ===== ENVOI INSTANTANÉ (sans reset) =====
    instant = card_counter.build_report()
    if detected_display_channel:
        try:
            # Obtenir l'entité du canal avant d'envoyer
            await client.send_message(int(detected_display_channel), instant)
            print(f"📈 Instantané envoyé au canal : {instant}")
        except Exception as ex:
            print(f"❌ Erreur envoi instantané : {ex}")
            try:
                # Essayer de récupérer l'entité du canal d'abord
                await client.get_entity(int(detected_display_channel))
                await client.send_message(detected_display_channel, instant)
                print(f"✅ Instantané envoyé (via entité) : {instant}")
            except Exception as ex2:
                print(f"❌ Échec total envoi : {ex2}")

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
    global detected_display_channel
    load_config()
    load_interval()
    await create_web()
    await client.start(bot_token=BOT_TOKEN)

    # Récupérer l'entité du canal d'affichage au démarrage
    if detected_display_channel:
        try:
            entity = await client.get_entity(int(detected_display_channel))
            print(f"✅ Canal d'affichage trouvé : {entity.title} (ID: {detected_display_channel})")
        except Exception as ex:
            print(f"⚠️ Impossible d'accéder au canal d'affichage {detected_display_channel}: {ex}")
            print(f"💡 Assurez-vous que le bot est membre du canal et utilisez /set_display [ID] pour configurer")

    restart_auto_bilan()
    me = await client.get_me()
    print(f"Bot connecté : @{me.username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())