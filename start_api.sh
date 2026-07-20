#!/bin/bash
echo "🚀 Démarrage de l'API FastAPI en arrière-plan..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

echo "⏳ Attente du démarrage de l'API..."
sleep 3

echo "🌍 Création du tunnel public (localtunnel)..."
echo "L'API sera disponible sur : https://protocole-clinique-api.loca.lt"
npx localtunnel --port 8000 --subdomain protocole-clinique-api
