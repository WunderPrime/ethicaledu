# EthicalEdu — Plateforme de détection de plagiat (Projet PFA 2025/2026)

Application Django permettant aux étudiants de soumettre leurs travaux (PDF/DOCX),
aux enseignants de lancer une analyse de plagiat (comparaison + calcul de similarité),
et aux administrateurs de gérer les utilisateurs et la configuration du système.

## Lancement avec Docker (recommandé)

La façon la plus simple de lancer le projet sans installer Python ou les dépendances manuellement.

**Prérequis :** avoir [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé.

```bash
# 1. Construire et lancer le projet
docker-compose up --build
```

L'application démarre automatiquement sur http://localhost:8000

Un compte **admin** est créé automatiquement au premier démarrage :
- Nom d'utilisateur : `admin`
- Mot de passe : `AdminEthical2026`

> Change le mot de passe dès la première connexion via "Gérer les utilisateurs".

Pour arrêter le projet :
```bash
docker-compose down
```

Les fichiers uploadés et la base de données sont conservés entre les redémarrages grâce aux volumes Docker.

---

## Installation sans Docker (développement local)

## Installation sans Docker (développement local)

```bash
# 1. Créer un environnement virtuel (recommandé)
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
venv\Scripts\activate             # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Appliquer les migrations
python manage.py migrate

# 4. Créer un compte administrateur
python manage.py createsuperuser

# 5. Lancer le serveur de développement
python manage.py runserver
```

L'application est ensuite accessible sur http://127.0.0.1:8000/

## Création des comptes Étudiant / Enseignant / Admin

Le formulaire d'inscription (`/inscription/`) permet de créer un compte Étudiant
ou Enseignant directement.

Le compte **Administrateur** se crée en une seule commande (User superuser +
Profil Admin créés ensemble) :

```bash
python manage.py creer_admin --username admin --email admin@emsi.ma --password votreMotDePasse
```

ou en mode interactif, sans arguments (le mot de passe est alors masqué à la saisie) :

```bash
python manage.py creer_admin
```

L'administrateur se connecte ensuite normalement sur `/connexion/`, comme les
autres utilisateurs (l'authentification est commune aux 3 rôles) — il est
automatiquement redirigé vers son tableau de bord dédié.

## Structure du projet

```
projet_django/
├── manage.py
├── settings.py / urls.py / wsgi.py / asgi.py
├── db.sqlite3
├── requirements.txt
├── media/travaux/          # fichiers soumis par les étudiants
└── detection/
    ├── models.py           # Profil, Travail, Analyse, RapportPlagiat, ...
    ├── views.py             # toutes les vues (Étudiant / Enseignant / Admin)
    ├── forms.py
    ├── urls.py
    ├── admin.py
    ├── extraction.py        # extraction de texte PDF / DOCX
    ├── similarite.py         # algorithmes Jaccard / cosinus, détection de passages
    ├── management/commands/creer_admin.py   # commande de création du compte Admin
    └── templates/
        ├── detection/        # templates de l'application
        └── registration/     # login / inscription
```

## Fonctionnalités implémentées

- Authentification (Étudiant / Enseignant / Admin) avec rôle stocké dans `Profil`
- Soumission de travaux PDF / DOCX / TXT avec extraction automatique du texte
- Analyse de plagiat : comparaison avec tous les autres travaux de la base,
  calcul du taux de similarité (Jaccard ou cosinus, au choix)
- Génération d'un rapport détaillé avec mise en évidence des passages similaires
- Historique des soumissions (vue Étudiant et vue globale Enseignant)
- Gestion des utilisateurs (Enseignant et Admin)
- Configuration du système : seuil d'alerte, taille des n-grammes, algorithme par défaut
- Tableau de bord statistique (Admin) : nombre d'utilisateurs/travaux/analyses, taux moyen
  de similarité, nombre de travaux suspects, et graphique d'évolution des soumissions et
  analyses sur les 6 derniers mois

## Algorithmes de similarité (sans IA)

- **Indice de Jaccard** : `|A ∩ B| / |A ∪ B|` sur des ensembles de n-grammes de mots
- **Similarité cosinus** : produit scalaire normalisé sur des vecteurs de fréquence de mots
- **Détection de passages similaires** : recherche de séquences de mots consécutifs communes
