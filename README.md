# 🤖 Bot Auto-Postulation CreatorsArea (Freelance Développeur)

Ce bot surveille en continu et en temps réel les nouvelles offres de développement publiées sur **CreatorsArea.fr**, filtre intelligemment les missions selon vos compétences (Code pur, Web, Bots, Scraping, API, SaaS, Automatisation) et **postule automatiquement et instantanément** avec votre portfolio.

---

## ⚡ Caractéristiques Principales

- 🚀 **Candidature Ultra-Rapide** : Détection et postulation dès la première seconde de publication d'une offre.
- 🎯 **Filtrage Intelligent des Compétences** :
  - ✅ **Inclus (Code Pur & IA)** : Sites web (React, Vue, Next.js, WordPress, etc.), Bots (Discord, Telegram, Vinted), Web Scraping, Scripts Python, Backend (Node, FastAPI, Laravel), SaaS, Extensions Chrome, DevOps.
  - ❌ **Exclus (Jeux / Modding / Graphisme)** : FiveM, GTA V, GMod, Roblox, Minecraft, DayZ, Hytale, Modélisation 3D / Blender, Level Design, Graphisme pur sans code.
- 💬 **Notifications Discord Webhook Riches** : Alertes instantanées sur votre serveur avec embed détaillé (titre, prix, tags, lien direct vers l'offre).
- 💾 **Mémoire & Anti-Doublon** : Base de données locale SQLite (`offers.db`) pour ne jamais repostuler deux fois à la même offre.
- 🛡️ **Mode Simulation (Dry-Run)** : Permet de tester le comportement du bot sans envoyer de vraies candidatures sur le site.
- 🤖 **Validation IA Optionnelle** : Possibilité d'activer une validation supplémentaire par IA (Gemini, OpenAI, Groq).

---

## 📦 Installation

1. **Cloner ou ouvrir le dossier du projet** :
   ```bash
   cd botOffreDev
   ```

2. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration (`.env`)

Copiez le fichier `.env.example` en `.env` et ajustez vos paramètres :

```env
# Token d'authentification 'creators_area_token'
CREATORS_AREA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5...

# Lien de votre portfolio ou profil GitHub envoyé lors de la candidature
PORTFOLIO_URL=https://github.com/YelloWorld5847/

# Intervalle de vérification en secondes (10s recommandé)
POLL_INTERVAL_SECONDS=10

# Accepter les offres bénévoles (true/false)
ALLOW_VOLUNTEER=true

# Budget minimum en euros pour postuler (0 = tout accepter)
MIN_PRICE=0

# URL de votre Webhook Discord (laisser vide si désactivé)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Mode Dry-Run (true = simulation, false = candidatures réelles)
DRY_RUN=false
```

### 🔑 Comment récupérer votre token CreatorsArea ?
1. Rendez-vous sur [creatorsarea.fr](https://creatorsarea.fr) et connectez-vous avec votre compte Discord.
2. Ouvrez la console du navigateur (`F12` ou `Ctrl + Maj + I`) > Onglet **Application** (ou **Stockage**) > **Cookies** > `https://creatorsarea.fr`.
3. Copiez la valeur du cookie `creators_area_token` et collez-la dans votre `.env`.

---

## 🚀 Utilisation

### 1. Tester la connexion à votre compte
```bash
python run.py --test-token
```

### 2. Tester le filtre sur les offres d'exemple
```bash
python run.py --test-eval
```

### 3. Lancer en mode Simulation (Dry-Run)
```bash
python run.py --dry-run
```

### 4. Lancer en direct (Postulation réelle automatique)
```bash
python run.py --live
```

### 5. Consulter l'historique des offres traitées
```bash
python run.py --history
```

---

## 🖥️ Lancer en tâche de fond (VPS / Linux / Windows)

### Sur Linux (avec PM2 ou Systemd)
```bash
# Avec PM2 :
pm2 start "python run.py --live" --name creatorsarea-bot
```

### Sur Windows
Vous pouvez simplement lancer le script dans un terminal PowerShell ou créer un fichier `.bat` :
```bat
@echo off
python run.py --live
pause
```
