#!/bin/sh

echo "=== EthicalEdu — Démarrage ==="

# Appliquer les migrations
echo "→ Application des migrations..."
python manage.py migrate --noinput

# Créer un compte admin par défaut si aucun n'existe
echo "→ Vérification du compte admin..."
python manage.py shell -c "
from django.contrib.auth.models import User
from detection.models import Profil
if not User.objects.filter(is_superuser=True).exists():
    u = User.objects.create_superuser('admin', 'admin@ethicaledu.ma', 'AdminEthical2026')
    Profil.objects.create(user=u, role=Profil.ADMIN, niveau_acces=3)
    print('Compte admin créé : admin / AdminEthical2026')
else:
    print('Compte admin déjà existant.')
"

# Collecter les fichiers statiques
echo "→ Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "=== Lancement du serveur sur 0.0.0.0:8000 ==="
exec python manage.py runserver 0.0.0.0:8000
