# AUTA Gestion

SaaS de gestion pour carrosseries : dossiers, extraction de rapports d’expertise, devis, atelier et facturation.

## Stack

- **Frontend** : React (Vite) + Tailwind CSS
- **Backend** : FastAPI (Python)
- **Base** : SQLite par défaut (PostgreSQL via Docker Compose)

## Démarrage rapide

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # si besoin
python seed.py         # données démo
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Ouvrir [http://localhost:5173](http://localhost:5173).

### Compte démo

| Email | Mot de passe | Rôle |
|-------|--------------|------|
| directeur@auta.demo | auta123 | Directeur |

MVP : un seul rôle utilisateur (directeur) avec accès complet.

### PostgreSQL (optionnel)

```bash
docker compose up -d db
```

Dans `backend/.env` :

```
DATABASE_URL=postgresql://auta:auta@localhost:5432/auta_gestion
```

Puis relancer `python seed.py`.

### Extraction IA — Grok (xAI)

Sans clé, l’extraction PDF utilise un parseur heuristique (limité).

Dans `backend/.env` :

```
GROK_API_KEY=xai-...
GROK_BASE_URL=https://api.x.ai/v1
GROK_MODEL=grok-3-mini
```

Clé à créer sur [console.x.ai](https://console.x.ai/). Relancer uvicorn après modification.

## Parcours MVP

1. Login → Accueil (compteurs)
2. Nouveau dossier → photo → PDF expertise → corriger → valider
3. Générer devis → éditer lignes si besoin → PDF → accepter
4. Atelier : changer les étapes / assigner un utilisateur
5. Facturer → PDF → marquer payée
6. Clôturer (Livré) — l’atelier n’affiche plus les dossiers clôturés

## Mettre en ligne (ami / téléphone partout)

GitHub héberge le **code** + le **frontend**. L’API tourne sur **Render** (gratuit) car GitHub Pages ne peut pas exécuter Python.

### Étape A — Repo GitHub

```bash
cd auta-gestion
git init
git add .
git commit -m "AUTA Gestion — prêt pour déploiement"
gh repo create auta-gestion --public --source=. --remote=origin --push
```

### Étape B — API sur Render (5 min)

1. Va sur [render.com](https://render.com) → **New** → **Blueprint** → connecte le repo
2. Valide `render.yaml` (API + Postgres)
3. Dans les variables Render, mets par exemple :
   ```
   CORS_ORIGINS=https://TON_USER.github.io
   ```
4. Note l’URL de l’API, ex. `https://auta-gestion-api.onrender.com`

### Étape C — Frontend sur GitHub Pages

1. Repo → **Settings** → **Pages** → Source : **GitHub Actions**
2. Repo → **Settings** → **Secrets and variables** → **Actions** → **Variables**  
   Ajoute `VITE_API_URL` = `https://auta-gestion-api.onrender.com` (sans `/` final)
3. Push sur `main` → le workflow **Deploy frontend to GitHub Pages** construit et publie
4. URL publique : `https://TON_USER.github.io/auta-gestion/`

### Sur le téléphone

Ouvre l’URL GitHub Pages → Partager → **Sur l’écran d’accueil**.  
Compte démo : `directeur@auta.demo` / `auta123` (créé auto au 1er démarrage API).

> Render free s’endort après inactivité (~1 min au réveil). Pour un usage pro, passe en plan payant.

## Structure

```
auta-gestion/
  backend/     FastAPI + SQLAlchemy
  frontend/    Vite React
  docker-compose.yml
```
