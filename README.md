# 🧠 Décodeur de Pensées

> Application web stateless qui transforme un "braindump" audio en liste de tâches structurée grâce à l'IA Mistral.

## Fonctionnement

1. L'utilisateur **enregistre sa voix** via le micro du navigateur.
2. Le backend **transcrit l'audio** avec Voxtral (Mistral).
3. Un modèle texte Mistral **extrait les tâches** (titre, description, priorité).
4. Le résultat est affiché sous forme de **cartes To-Do**.

## Stack Technique

| Composant | Technologie |
|-----------|------------|
| Backend | FastAPI (async) |
| IA — Transcription | Voxtral (SDK Mistral) |
| IA — Extraction | Mistral Small |
| Validation | Pydantic |
| Frontend | Vanilla HTML / CSS / JS |
| Déploiement | Docker |

## Démarrage Rapide

### Prérequis

- Docker installé
- Une clé API Mistral

### Lancement

```bash
# 1. Copier le fichier d'environnement
cp .env.example .env
# 2. Renseigner votre clé API Mistral dans .env

# 3. Construire et lancer
docker build -t decodeur-pensees .
docker run --env-file .env -p 8000:8000 decodeur-pensees
```

Ouvrir **http://localhost:8000** dans le navigateur.

### Développement local (sans Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Structure du Projet

```
projet-mistral/
├── backend/
│   ├── app/
│   │   ├── main.py              # App FastAPI + route /api/process-audio
│   │   ├── config.py            # Settings (MISTRAL_API_KEY)
│   │   ├── schemas.py           # Modèles Pydantic
│   │   └── services/
│   │       └── mistral_service.py   # Appels SDK Mistral
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── Dockerfile
├── .env.example
└── README.md
```

## Licence

Projet réalisé dans le cadre d'un test technique Mistral AI.
