# Plateforme de Préparation à l'Embauche — IA Mistral

Application web de préparation à l'embauche propulsée par **Mistral AI**. Elle couvre l'ensemble du processus candidat : recherche d'offres, rédaction de lettre de motivation, entraînement à l'entretien (texte, voix, webcam) et historique personnalisé.

---

## Fonctionnalités

| Module | Description |
|--------|-------------|
| **Lettre de motivation** | Génération personnalisée à partir du CV + offre, révision par instructions, sauvegarde dans l'historique |
| **Entretien simulé** | Recruteur IA exigeant, questions adaptées au profil et à l'offre, réponses texte ou vocales |
| **Analyse visuelle** | Analyse du langage corporel (posture, regard, confiance) via la webcam à partir de captures régulières |
| **Feedback d'entretien** | Rapport structuré avec score, points forts, axes d'amélioration et conseil actionnable |
| **Recherche d'emploi** | Recherche d'offres via JSearch / Adzuna, score de correspondance avec le CV, sauvegarde des offres |
| **Historique** | Lettres de motivation, rapports d'entretien et offres sauvegardées, accessibles et supprimables |

---

## Stack technique

- **Backend** : FastAPI + Uvicorn, SQLAlchemy (SQLite)
- **Frontend** : HTML / CSS / JavaScript vanilla
- **IA** : Mistral AI SDK (texte, vision, voix, embeddings)
- **Infra** : Docker + Docker Compose

---

## Prérequis

- [Docker](https://www.docker.com/) et Docker Compose installés
- Une clé API **Mistral AI** (obligatoire)
- Optionnel : clés **JSearch** (RapidAPI) et/ou **Adzuna** pour la recherche d'emploi

---

## Installation et lancement

### 1. Cloner le dépôt

```bash
git clone <url-du-repo>
cd projet-mistral
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
```

Éditer `.env` et renseigner au minimum :

```env
MISTRAL_API_KEY=votre_clé_mistral

# Optionnel — recherche d'emploi
JSEARCH_API_KEY=votre_clé_jsearch
ADZUNA_APP_ID=votre_app_id
ADZUNA_API_KEY=votre_clé_adzuna

# Optionnel — sécurité JWT (changer en production)
SECRET_KEY=une-clé-secrète-longue-et-aléatoire
```

### 3. Lancer l'application

```bash
docker compose up --build
```

L'application est accessible sur [http://localhost:8000](http://localhost:8000).

---

## Guide d'utilisation

### Créer un compte

Cliquer sur **Connexion** en haut à droite → **Créer un compte**. Le compte permet de sauvegarder lettres, rapports d'entretien et offres d'emploi dans l'historique.

---

### Lettre de motivation

1. Aller sur **Lettre de motivation**
2. Importer le CV (PDF ou TXT) ou coller son texte
3. Coller le texte de l'offre d'emploi ciblée
4. Choisir la langue (français par défaut)
5. Optionnel : joindre des exemples de lettres pour guider le style
6. Cliquer **Générer**

Une fois la lettre affichée, il est possible de la **réviser** en décrivant la modification souhaitée (ex. *"Rends-la plus concise"*, *"Mets davantage l'accent sur mon expérience en Python"*). Chaque révision est sauvegardée dans l'historique.

---

### Entretien simulé

1. Aller sur **Entretien**
2. Importer le CV et coller l'offre
3. Optionnel : activer la **webcam** pour l'analyse visuelle du langage corporel
4. Cliquer **Démarrer l'entretien**

Le recruteur IA pose des questions adaptées au CV et à l'offre. Répondre par :
- **Texte** : taper la réponse et valider
- **Voix** : cliquer sur le micro, parler, relâcher — la réponse est transcrite automatiquement

Lorsque le recruteur conclut l'entretien, un **rapport de feedback** est généré automatiquement avec :
- Un score sur 10
- Les points forts et les axes d'amélioration
- Un conseil actionnable
- Si la webcam était active : un rapport d'analyse visuelle (posture, regard, confiance)

---

### Recherche d'emploi

1. Aller sur **Recherche d'emploi**
2. Saisir des mots-clés et une localisation
3. Optionnel : coller le CV pour obtenir un **score de correspondance** avec chaque offre
4. Cliquer sur une offre pour la consulter, la **sauvegarder** ou l'envoyer directement vers le module Lettre de motivation

---

### Historique

L'onglet **Historique** regroupe :
- Les lettres de motivation générées et révisées
- Les rapports d'entretien avec scores et feedback
- Les offres d'emploi sauvegardées

Chaque entrée peut être consultée en détail ou supprimée.

---

## Description des services

| Service | Modèle | Rôle |
|---------|--------|------|
| `cover_letter_service` | `mistral-small-latest` | Génère une lettre de motivation à partir du CV et de l'offre ; révise une lettre existante selon les instructions de l'utilisateur |
| `interview_service` | `mistral-small-latest` | Joue le rôle d'un recruteur exigeant en conversation multi-tours ; génère un rapport de feedback structuré à l'issue de l'entretien |
| `vision_service` | `pixtral-12b-2409` | Analyse jusqu'à 5 captures webcam (sous-échantillonnées sur toute la durée) pour évaluer le langage corporel : expressions, posture, regard, confiance |
| `voice_service` | `voxtral-mini-latest` | Transcrit les fichiers audio (WebM) enregistrés par le navigateur en texte |
| `embedding_service` | `mistral-embed` | Calcule des embeddings vectoriels pour mesurer la similarité entre le CV et les offres d'emploi |
| `job_service` | — | Agrège les offres d'emploi depuis JSearch (RapidAPI) et Adzuna ; calcule un score de correspondance avec le CV via les embeddings |
| `auth_service` | — | Gère l'inscription, la connexion, le hachage des mots de passe (bcrypt) et l'émission / la vérification des tokens JWT |

Les modèles sont configurables via les variables d'environnement `TEXT_MODEL`, `VISION_MODEL`, `VOICE_MODEL` et `EMBED_MODEL`.

---

## Variables d'environnement

| Variable | Obligatoire | Défaut | Description |
|----------|:-----------:|--------|-------------|
| `MISTRAL_API_KEY` | ✅ | — | Clé API Mistral AI |
| `SECRET_KEY` | — | `dev-secret-change-me-in-production` | Clé de signature JWT |
| `DATABASE_URL` | — | `sqlite:///data/data.db` | URL de connexion à la base de données |
| `TEXT_MODEL` | — | `mistral-small-latest` | Modèle de texte |
| `VISION_MODEL` | — | `pixtral-12b-2409` | Modèle de vision |
| `VOICE_MODEL` | — | `voxtral-mini-latest` | Modèle de transcription vocale |
| `EMBED_MODEL` | — | `mistral-embed` | Modèle d'embeddings |
| `JSEARCH_API_KEY` | — | — | Clé RapidAPI pour JSearch |
| `ADZUNA_APP_ID` | — | — | App ID Adzuna |
| `ADZUNA_API_KEY` | — | — | Clé API Adzuna |

---

## Structure du projet

```
projet-mistral/
├── backend/
│   └── app/
│       ├── main.py              # Point d'entrée FastAPI
│       ├── config.py            # Configuration (variables d'env)
│       ├── database.py          # Connexion SQLAlchemy
│       ├── models.py            # Modèles ORM
│       ├── schemas.py           # Schémas Pydantic
│       ├── utils.py             # Utilitaires (extraction PDF/TXT…)
│       ├── routers/             # Routes API
│       │   ├── auth.py
│       │   ├── cover_letter.py
│       │   ├── interview.py
│       │   ├── history.py
│       │   └── jobs.py
│       └── services/            # Logique métier
│           ├── auth_service.py
│           ├── cover_letter_service.py
│           ├── interview_service.py
│           ├── vision_service.py
│           ├── voice_service.py
│           ├── embedding_service.py
│           └── job_service.py
├── frontend/                    # Interface HTML/CSS/JS
├── data/                        # Base SQLite (créée automatiquement)
├── Dockerfile
├── docker-compose.yml
└── .env
```
