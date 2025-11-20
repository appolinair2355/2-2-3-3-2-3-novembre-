Telegram Card Counter Bot - Déploiement Render.com
🎯 Configuration Render.com
Prérequis
Compte Render.com (gratuit)
Telegram API credentials (my.telegram.org)
Bot Token (@BotFather)
Étapes de déploiement
Créer un Web Service sur Render.com

Aller sur https://render.com
Cliquer sur "New +" → "Web Service"
Connecter votre repo GitHub ou uploader le code
Configuration du service

Name: telegram-card-counter-bot
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: python main.py
Variables d'environnement (dans l'onglet Environment)

API_ID=votre_api_id
API_HASH=votre_api_hash
BOT_TOKEN=votre_bot_token
ADMIN_ID=votre_telegram_user_id
PORT=10000
Déployer

Cliquer sur "Create Web Service"
Attendre la fin du déploiement (5-10 minutes)
Vérifier les logs pour confirmer: "Bot connecté"
📊 Fonctionnement
Messages reconnus
Le bot compte les paires de cartes dans les messages :

2/2 : 2 cartes dans chaque groupe
2/3 : 2 cartes dans le 1er groupe, 3 dans le 2ème
3/2 : 3 cartes dans le 1er groupe, 2 dans le 2ème
3/3 : 3 cartes dans chaque groupe
Exemples de messages
#N1392. ✅6(6♠️5♥️5♣️) - 4(8♥️7♣️9♦️) #T10
#N1394. 7(7♠️K♠️) - ✅8(Q♠️8♥️) #T15
Commandes du Bot
/start - Démarrer le bot
/status - Voir la configuration
/set_stat [id] - Configurer canal source
/set_display [id] - Configurer canal affichage
/bilan - Rapport immédiat
/reset - Réinitialiser compteurs
⚠️ Important
Version Python
Python 3.11.10 est OBLIGATOIRE

❌ Python 3.13+ causera des erreurs
✅ runtime.txt contient python-3.11.10
Port
Le port 10000 est configuré pour Render.com

Canaux pré-configurés
Canal source: -1002682552255
Canal affichage: -1003309666471
Vous pouvez les modifier via les commandes du bot.

🚀 Prêt pour le déploiement !
