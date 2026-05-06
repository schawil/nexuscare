# NexusCare

Application Android de contrôle parental — Projet Master 1 Systèmes & Réseaux

## Structure
```
nexuscare/
├── backend/          # FastAPI + SQLite
├── android-parent/   # APK Parent (Android Studio)
├── android-child/    # APK Enfant (Android Studio)
└── docs/             # Spécifications, diagrammes
```

## Lancer le backend
```bash
cd backend
source .venv/bin/activate
uvicorn nexuscare.main:app --host 0.0.0.0 --port 8000 --reload
```

## Exposer pour les téléphones (demo)
```bash
ngrok http 8000
```
