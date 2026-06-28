# Image de base Python légère
FROM python:3.12-slim

# Variables d'environnement pour éviter les fichiers .pyc et les buffers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app

# Installer les dépendances système nécessaires pour PyPDF2 et python-docx
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le projet
COPY . .

# Créer les dossiers media et staticfiles s'ils n'existent pas
RUN mkdir -p media/travaux staticfiles

# Exposer le port Django
EXPOSE 8000

# Script de démarrage
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
