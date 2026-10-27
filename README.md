# Bot Auto-Postulation CreatorsArea

Ce bot surveille en temps reel les offres de developpement publiees sur creatorsarea.fr, filtre les missions selon vos competences (Web, Bots, Scraping, API, SaaS, Automatisation) et postule automatiquement avec votre portfolio.

## Installation

1. Cloner ou ouvrir le dossier du projet :
```bash
cd botOffreDev
```

2. Installer les dependances :
```bash
pip install -r requirements.txt
```

## Gestion des Tokens et Authentification

Le token CreatorsArea expire au bout de 7 jours. Vous avez 3 methodes pour le gerer facilement :

### Methode 1 : Connexion automatique via Token Discord (Recommande)

Ajoutez votre token utilisateur Discord dans `.env` :
```env
DISCORD_USER_TOKEN=votre_token_discord
```
Le bot effectuera automatiquement le handshake OAuth Discord des que le token CreatorsArea expire. Vous n'avez rien a faire manuellement.

Pour tester le renouvellement immediat :
```bash
python run.py --refresh-token
```

### Methode 2 : Commande rapide de mise a jour

Pour mettre a jour le token CreatorsArea sans editer le fichier a la main :
```bash
python run.py --set-token <NOUVEAU_TOKEN>
```
La commande verifie la validite du token, l'enregistre dans `.env` et relance le processus PM2 si present.

Pour verifier l'etat et le temps restant du token actuel :
```bash
python run.py --check-token
```

### Methode 3 : Favori de navigateur (Bookmarklet 1 clic)

Creez un favori dans Chrome/Firefox avec cette URL :
```javascript
javascript:(function(){const m=document.cookie.match(/creators_area_token=([^;]+)/);if(!m){alert("Non connecte sur CreatorsArea");return;}const t=m[1];navigator.clipboard.writeText("python run.py --set-token "+t);alert("Commande copiee dans le presse-papier :\npython run.py --set-token "+t.substring(0,20)+"...");})();
```
En cliquant sur ce favori lorsque vous etes sur creatorsarea.fr, la commande complete `python run.py --set-token ...` est copiee dans votre presse-papier. Il ne reste plus qu'a la coller dans votre terminal.

### Methode 4 : Extension Chrome

Le dossier `extension/` contient une extension Chrome non compressee.
1. Rendez-vous sur `chrome://extensions/`
2. Activez le mode developpeur.
3. Cliquez sur "Charger l'extension non empaquetee" et selectionnez le dossier `botOffreDev/extension`.
4. Sur creatorsarea.fr, cliquez sur l'icone de l'extension pour copier le token ou la commande.

## Commandes d'execution

### Mode Simulation (Dry-Run)
```bash
python run.py --dry-run
```

### Mode Reel
```bash
python run.py --live
```

### Historique
```bash
python run.py --history
```
