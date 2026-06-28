from django.urls import path
from . import views

app_name = 'detection'

urlpatterns = [
    # Accueil / Authentification
    path('', views.accueil, name='home'),
    path('connexion/', views.ConnexionView.as_view(), name='login'),
    path('deconnexion/', views.DeconnexionView.as_view(), name='logout'),
    path('inscription/', views.InscriptionView.as_view(), name='inscription'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Étudiant
    path('etudiant/dashboard/', views.dashboard_etudiant, name='dashboard_etudiant'),
    path('etudiant/soumettre/', views.soumettre_travail, name='soumettre_travail'),
    path('etudiant/historique/', views.historique_etudiant, name='historique_etudiant'),

    # Rapport (commun Étudiant / Enseignant / Admin)
    path('travail/<int:travail_id>/rapport/', views.consulter_rapport, name='consulter_rapport'),
    path('rapport/<int:pk>/', views.detail_rapport, name='detail_rapport'),

    # Enseignant
    path('enseignant/dashboard/', views.dashboard_enseignant, name='dashboard_enseignant'),
    path('enseignant/analyser/<int:travail_id>/', views.lancer_analyse, name='lancer_analyse'),
    path('enseignant/historique/', views.historique_enseignant, name='historique_enseignant'),

    # Gestion des utilisateurs (Enseignant + Admin)
    path('utilisateurs/', views.gerer_utilisateurs, name='gerer_utilisateurs'),
    path('utilisateurs/creer/', views.creer_utilisateur, name='creer_utilisateur'),
    path('utilisateurs/<int:pk>/modifier/', views.modifier_utilisateur, name='modifier_utilisateur'),
    path('utilisateurs/<int:pk>/supprimer/', views.supprimer_utilisateur, name='supprimer_utilisateur'),

    # Admin
    path('admin-dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('configuration/', views.configurer_systeme, name='configurer_systeme'),
]
