# 🚀 Déploiement sur Render.com

## Configuration Render.com

### 1️⃣ Créer un Web Service
- Aller sur https://render.com
- Cliquer sur **"New +"** → **"Web Service"**
- Connecter votre repo GitHub ou uploader le fichier `deployment.zip`

### 2️⃣ Configuration du Service

| Paramètre | Valeur |
|-----------|--------|
| **Name** | `telegram-card-counter-bot` |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python main.py` |
| **Port** | `10000` |

### 3️⃣ Variables d'Environnement (Environment)

Ajouter dans l'onglet "Environment" de Render.com :

```
API_ID=<votre_api_id>
API_HASH=<votre_api_hash>
BOT_TOKEN=<votre_bot_token>
ADMIN_ID=<votre_telegram_user_id>
PORT=10000
```

**Comment obtenir ces valeurs :**

1. **API_ID & API_HASH** - https://my.telegram.org/apps
   - Aller sur "API development tools"
   - Créer une application
   - Copier les valeurs

2. **BOT_TOKEN** - https://t.me/BotFather
   - Envoyer `/newbot`
   - Suivre les instructions
   - Copier le token

3. **ADMIN_ID** - Votre ID Telegram
   - Envoyer `/start` à @userinfobot
   - Copier votre ID

### 4️⃣ Déployer
- Cliquer sur **"Create Web Service"**
- Attendre 5-10 minutes
- Vérifier les logs pour confirmer : **"Bot connecté"**

## ✅ Vérification

Une fois déployé, testez le bot avec `/start` dans Telegram. Vous devriez voir : 
```
🎯 Bot Compteur de cartes prêt !
```

## 📋 Commandes du Bot

- `/start` - Démarrer le bot
- `/status` - Voir la configuration
- `/set_stat [id]` - Configurer canal source
- `/set_display [id]` - Configurer canal affichage
- `/bilan` - Rapport immédiat
- `/reset` - Réinitialiser compteurs

## 🐛 Troubleshooting

**Erreur : "API ID or Hash cannot be empty"**
- Vérifier que les variables d'environnement sont bien définies dans Render.com

**Bot ne réagit pas**
- Vérifier les logs dans Render.com
- Vérifier que le canal source est bien configuré

**Port déjà utilisé**
- Le port 10000 doit être libre sur Render.com (c'est le port par défaut)
