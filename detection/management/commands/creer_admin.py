"""
Commande personnalisée : crée en une seule étape un compte Administrateur
(User superuser + Profil avec role=ADMIN).

Usage :
    python manage.py creer_admin
    python manage.py creer_admin --username admin --email admin@emsi.ma --password monmotdepasse
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from getpass import getpass

from detection.models import Profil


class Command(BaseCommand):
    help = "Crée un compte Administrateur complet (User + Profil ADMIN) en une seule commande."

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help="Nom d'utilisateur de l'admin")
        parser.add_argument('--email', type=str, help="Adresse e-mail de l'admin")
        parser.add_argument('--password', type=str, help="Mot de passe (sinon demandé de façon masquée)")

    def handle(self, *args, **options):
        username = options.get('username') or input("Nom d'utilisateur de l'admin : ")
        email = options.get('email') or input("Adresse e-mail : ")
        password = options.get('password') or getpass("Mot de passe : ")

        if User.objects.filter(username=username).exists():
            raise CommandError(f"L'utilisateur « {username} » existe déjà.")

        try:
            user = User.objects.create_superuser(
                username=username, email=email, password=password
            )
        except IntegrityError as exc:
            raise CommandError(str(exc))

        Profil.objects.update_or_create(
            user=user,
            defaults={'role': Profil.ADMIN, 'niveau_acces': 3}
        )

        self.stdout.write(self.style.SUCCESS(
            f"Compte administrateur « {username} » créé avec succès (User + Profil ADMIN)."
        ))
