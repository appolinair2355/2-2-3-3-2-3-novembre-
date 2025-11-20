# joueu2 - Compteur de Cartes Telegram

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

4. **Déployer**
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

🎯 **joueu2** - Prêt pour déploiement Replit!

## 📋 Configuration Canaux Pré-Configurée
- **Canal Source**: -1002682552255 (lecture des messages de cartes)
- **Canal Affichage**: -1002674389383 (envoi des rapports)
- Ces canaux sont déjà configurés dans `config.py`
- Modifiez `config.py` avant déploiement si nécessaire
- **Comptage**: 1er groupe uniquement
