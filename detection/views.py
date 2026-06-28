import os
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q, Avg, Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView

from .models import Travail, Analyse, RapportPlagiat, SourceSimilaire, Profil, ConfigurationSysteme
from .forms import (
    InscriptionForm, SoumissionTravailForm, LancerAnalyseForm,
    ConfigurationForm, GestionUtilisateurForm
)
from .extraction import extraire_texte
from .similarite import calculer_taux, comparer_avec_corpus, detecter_passages_similaires


# ──────────────────────────────────────────────
# Décorateurs de rôle
# ──────────────────────────────────────────────

def est_enseignant(user):
    return user.is_authenticated and hasattr(user, 'profil') and user.profil.est_enseignant()


def est_admin(user):
    return user.is_authenticated and (
        user.is_superuser or (hasattr(user, 'profil') and user.profil.est_admin())
    )


def est_etudiant(user):
    return user.is_authenticated and hasattr(user, 'profil') and user.profil.est_etudiant()


# ──────────────────────────────────────────────
# Accueil / Authentification — S'authentifier
# ──────────────────────────────────────────────

def accueil(request):
    return render(request, 'detection/accueil.html')


class ConnexionView(LoginView):
    """Cas d'usage : S'authentifier (commun aux 3 acteurs)."""
    template_name = 'registration/login.html'

    def get_success_url(self):
        return reverse_lazy('detection:dashboard')


class DeconnexionView(LogoutView):
    next_page = reverse_lazy('detection:home')


class InscriptionView(CreateView):
    """Inscription — créé un User + Profil (Étudiant ou Enseignant)."""
    form_class = InscriptionForm
    template_name = 'registration/inscription.html'
    success_url = reverse_lazy('detection:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Inscription réussie. Vous pouvez vous connecter.")
        return response


@login_required
def dashboard(request):
    """Redirige vers le tableau de bord adapté au rôle de l'utilisateur."""
    profil = getattr(request.user, 'profil', None)

    if request.user.is_superuser or (profil and profil.est_admin()):
        return redirect('detection:dashboard_admin')
    elif profil and profil.est_enseignant():
        return redirect('detection:dashboard_enseignant')
    elif profil and profil.est_etudiant():
        return redirect('detection:dashboard_etudiant')

    messages.warning(request, "Aucun rôle n'est associé à votre compte. Contactez un administrateur.")
    return redirect('detection:home')


# ──────────────────────────────────────────────
# ÉTUDIANT — Soumettre un travail «include» Extraire le texte
# ──────────────────────────────────────────────

@login_required
@user_passes_test(est_etudiant, login_url='detection:dashboard')
def dashboard_etudiant(request):
    travaux = Travail.objects.filter(etudiant=request.user)
    return render(request, 'detection/dashboard_etudiant.html', {'travaux': travaux})


@login_required
@user_passes_test(est_etudiant, login_url='detection:dashboard')
def soumettre_travail(request):
    """
    Cas d'usage : Soumettre un travail.
    Séquence : 5. soumettreTravail() → 6. enregistrerTravail() → 7. confirmation
               → 8. extraireTexte() «include» → 9. parserPDF/DOCX() → 10. texteExtrait()
               → 11. accuséRéception()
    """
    if request.method == 'POST':
        form = SoumissionTravailForm(request.POST, request.FILES)
        if form.is_valid():
            travail = form.save(commit=False)
            travail.etudiant = request.user
            travail.save()  # 6. enregistrerTravail()

            # 8-10. Extraction automatique du texte «include»
            try:
                chemin = travail.fichier.path
                texte = extraire_texte(chemin)
                travail.texte_extrait = texte
                travail.statut = 'extrait'
                travail.save()
                messages.success(
                    request,
                    "Travail soumis et texte extrait avec succès. "
                    "Votre enseignant pourra maintenant lancer l'analyse."
                )
            except Exception as exc:
                travail.statut = 'erreur'
                travail.save()
                messages.error(request, f"Travail soumis, mais l'extraction du texte a échoué : {exc}")

            return redirect('detection:dashboard_etudiant')
    else:
        form = SoumissionTravailForm()

    return render(request, 'detection/soumettre_travail.html', {'form': form})


@login_required
def consulter_rapport(request, travail_id):
    """
    Cas d'usage : Consulter le rapport.
    Accessible à l'étudiant propriétaire du travail et à l'enseignant.
    """
    travail = get_object_or_404(Travail, pk=travail_id)

    profil = getattr(request.user, 'profil', None)
    est_proprietaire = travail.etudiant_id == request.user.id
    a_le_droit = est_proprietaire or (profil and (profil.est_enseignant() or profil.est_admin()))

    if not a_le_droit:
        messages.error(request, "Vous n'avez pas accès à ce rapport.")
        return redirect('detection:dashboard')

    rapport = getattr(getattr(travail, 'analyse', None), 'rapport', None)

    return render(request, 'detection/consulter_rapport.html', {
        'travail': travail,
        'rapport': rapport,
    })


@login_required
@user_passes_test(est_etudiant, login_url='detection:dashboard')
def historique_etudiant(request):
    """Cas d'usage : Voir l'historique des soumissions (Étudiant)."""
    travaux = Travail.objects.filter(etudiant=request.user).order_by('-date_depot')
    return render(request, 'detection/historique.html', {'travaux': travaux, 'vue_enseignant': False})


# ──────────────────────────────────────────────
# ENSEIGNANT — Analyser «include» Comparer BDD «include» Générer rapport «include» Mettre en évidence
# ──────────────────────────────────────────────

@login_required
@user_passes_test(est_enseignant, login_url='detection:dashboard')
def dashboard_enseignant(request):
    travaux_en_attente = Travail.objects.filter(statut='extrait')
    analyses_recentes = Analyse.objects.select_related('travail').all()[:10]
    return render(request, 'detection/dashboard_enseignant.html', {
        'travaux_en_attente': travaux_en_attente,
        'analyses_recentes': analyses_recentes,
    })


@login_required
@user_passes_test(est_enseignant, login_url='detection:dashboard')
def lancer_analyse(request, travail_id):
    """
    Cas d'usage : Analyser le plagiat «include» Comparer avec la BDD
                  «include» Générer un rapport détaillé «include» Mettre en évidence les passages.

    Séquence :
    16. lancerAnalysePlagiat() → 17. analyser() «include»
    → 18. comparerBDD() «include» → 19. similarites[]
    → 20. calculerTaux() → 21. genererRapport() «include»
    → 22. mettreEnEvidencePassages() «include» → 23-24. affichage
    """
    travail = get_object_or_404(Travail, pk=travail_id)

    if travail.texte_extrait is None:
        messages.error(request, "Ce travail n'a pas encore de texte extrait.")
        return redirect('detection:dashboard_enseignant')

    if request.method == 'POST':
        form = LancerAnalyseForm(request.POST)
        if form.is_valid():
            algorithme = form.cleaned_data['algorithme']
            config = ConfigurationSysteme.get_config()

            # 17. analyser(travail) «include»
            analyse, _ = Analyse.objects.update_or_create(
                travail=travail,
                defaults={
                    'enseignant': request.user,
                    'algorithme': algorithme,
                }
            )

            # 18. comparerBDD(travail) «include» -> 19. similarites[]
            corpus = Travail.objects.exclude(pk=travail.pk).exclude(texte_extrait__isnull=True)
            resultats = comparer_avec_corpus(
                travail.texte_extrait, corpus,
                algorithme=algorithme, n=config.taille_ngramme
            )

            SourceSimilaire.objects.filter(analyse=analyse).delete()
            taux_max = 0.0
            passages_detectes = []

            for travail_source, score in resultats[:5]:
                SourceSimilaire.objects.create(
                    analyse=analyse, travail_source=travail_source, score_similarite=score
                )
                if score > taux_max:
                    taux_max = score
                # 22. mettreEnEvidencePassages() «include»
                if score > 0:
                    passages = detecter_passages_similaires(travail.texte_extrait, travail_source.texte_extrait)
                    for p in passages:
                        p['source'] = travail_source.titre
                    passages_detectes.extend(passages)

            # 20. calculerTaux()
            analyse.taux_plagiat = taux_max
            analyse.save()

            # 21. genererRapport(taux) «include»
            RapportPlagiat.objects.update_or_create(
                analyse=analyse,
                defaults={
                    'pourcentage': taux_max,
                    'passages_similaires': passages_detectes[:30],
                    'contenu_resume': (
                        f"Analyse réalisée avec l'algorithme {analyse.get_algorithme_display()}. "
                        f"Taux de similarité maximal détecté : {taux_max:.1f}%. "
                        f"{len(passages_detectes)} passage(s) similaire(s) identifié(s)."
                    ),
                }
            )

            travail.statut = 'analyse'
            travail.save()

            if taux_max >= config.seuil_alerte:
                messages.warning(
                    request,
                    f"Analyse terminée — taux de plagiat élevé : {taux_max:.1f}% "
                    f"(seuil d'alerte : {config.seuil_alerte}%)."
                )
            else:
                messages.success(request, f"Analyse terminée — taux de plagiat : {taux_max:.1f}%.")

            return redirect('detection:detail_rapport', pk=analyse.rapport.pk)
    else:
        form = LancerAnalyseForm()

    return render(request, 'detection/lancer_analyse.html', {'travail': travail, 'form': form})


@login_required
def detail_rapport(request, pk):
    """Affiche un RapportPlagiat avec passages mis en évidence."""
    rapport = get_object_or_404(RapportPlagiat, pk=pk)
    travail = rapport.analyse.travail

    profil = getattr(request.user, 'profil', None)
    est_proprietaire = travail.etudiant_id == request.user.id
    a_le_droit = est_proprietaire or (profil and (profil.est_enseignant() or profil.est_admin()))
    if not a_le_droit:
        messages.error(request, "Vous n'avez pas accès à ce rapport.")
        return redirect('detection:dashboard')

    sources = rapport.analyse.sources.select_related('travail_source').all()
    return render(request, 'detection/detail_rapport.html', {
        'rapport': rapport, 'travail': travail, 'sources': sources,
    })


@login_required
@user_passes_test(lambda u: est_enseignant(u) or est_admin(u), login_url='detection:dashboard')
def historique_enseignant(request):
    """Cas d'usage : Voir l'historique des soumissions (Enseignant — vue globale)."""
    travaux = Travail.objects.all().order_by('-date_depot')
    return render(request, 'detection/historique.html', {'travaux': travaux, 'vue_enseignant': True})


# ──────────────────────────────────────────────
# ADMIN — Gérer les utilisateurs
# ──────────────────────────────────────────────

@login_required
@user_passes_test(est_admin, login_url='detection:dashboard')
def gerer_utilisateurs(request):
    """Cas d'usage : Gérer les utilisateurs (réservé à l'Admin)."""
    requete = request.GET.get('q', '')
    utilisateurs = User.objects.select_related('profil').all().order_by('username')
    if requete:
        utilisateurs = utilisateurs.filter(
            Q(username__icontains=requete) | Q(email__icontains=requete)
        )
    return render(request, 'detection/gerer_utilisateurs.html', {
        'utilisateurs': utilisateurs, 'requete': requete,
    })


@login_required
@user_passes_test(est_admin, login_url='detection:dashboard')
def creer_utilisateur(request):
    if request.method == 'POST':
        form = GestionUtilisateurForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Utilisateur {user.username} créé avec succès.")
            return redirect('detection:gerer_utilisateurs')
    else:
        form = GestionUtilisateurForm()
    return render(request, 'detection/form_utilisateur.html', {'form': form, 'mode': 'creation'})


@login_required
@user_passes_test(est_admin, login_url='detection:dashboard')
def modifier_utilisateur(request, pk):
    user_cible = get_object_or_404(User, pk=pk)
    profil_cible, _ = Profil.objects.get_or_create(user=user_cible)

    if request.method == 'POST':
        form = GestionUtilisateurForm(request.POST, instance=user_cible, initial={'role': profil_cible.role})
        if form.is_valid():
            form.save()
            messages.success(request, f"Utilisateur {user_cible.username} modifié avec succès.")
            return redirect('detection:gerer_utilisateurs')
    else:
        form = GestionUtilisateurForm(instance=user_cible, initial={'role': profil_cible.role})

    return render(request, 'detection/form_utilisateur.html', {
        'form': form, 'mode': 'edition', 'utilisateur': user_cible,
    })


@login_required
@user_passes_test(est_admin, login_url='detection:dashboard')
def supprimer_utilisateur(request, pk):
    user_cible = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        nom = user_cible.username
        user_cible.delete()
        messages.success(request, f"Utilisateur {nom} supprimé avec succès.")
        return redirect('detection:gerer_utilisateurs')
    return render(request, 'detection/confirmer_suppression.html', {'utilisateur': user_cible})


# ──────────────────────────────────────────────
# ADMIN — Configurer le système
# ──────────────────────────────────────────────

@login_required
@user_passes_test(est_admin, login_url='detection:dashboard')
def dashboard_admin(request):
    """
    Tableau de bord administrateur — Figure 2.6.3 : Statistiques et suivi.
    Fournit les indicateurs d'utilisation de la plateforme : nombre de
    soumissions, analyses réalisées, taux moyen de similarité, et
    l'évolution des soumissions/analyses sur les 6 derniers mois.
    """
    aujourdhui = timezone.now()
    debut_periode = aujourdhui - timedelta(days=180)

    nb_travaux = Travail.objects.count()
    nb_analyses = Analyse.objects.count()
    taux_moyen = Analyse.objects.aggregate(moyenne=Avg('taux_plagiat'))['moyenne'] or 0.0
    nb_suspects = Analyse.objects.filter(
        taux_plagiat__gte=ConfigurationSysteme.get_config().seuil_alerte
    ).count()

    stats = {
        'nb_utilisateurs': User.objects.count(),
        'nb_etudiants': Profil.objects.filter(role=Profil.ETUDIANT).count(),
        'nb_enseignants': Profil.objects.filter(role=Profil.ENSEIGNANT).count(),
        'nb_travaux': nb_travaux,
        'nb_analyses': nb_analyses,
        'taux_moyen': round(taux_moyen, 1),
        'nb_suspects': nb_suspects,
    }

    # Évolution mensuelle des soumissions et des analyses (6 derniers mois)
    travaux_periode = Travail.objects.filter(date_depot__gte=debut_periode)
    analyses_periode = Analyse.objects.filter(date_analyse__gte=debut_periode)

    soumissions_par_mois = (
        travaux_periode
        .annotate(mois=TruncMonth('date_depot'))
        .values('mois')
        .annotate(total=Count('id'))
        .order_by('mois')
    )
    analyses_par_mois = (
        analyses_periode
        .annotate(mois=TruncMonth('date_analyse'))
        .values('mois')
        .annotate(total=Count('id'))
        .order_by('mois')
    )

    soumissions_dict = {s['mois'].strftime('%Y-%m'): s['total'] for s in soumissions_par_mois}
    analyses_dict = {a['mois'].strftime('%Y-%m'): a['total'] for a in analyses_par_mois}

    labels_mois = []
    soumissions_data = []
    analyses_data = []
    curseur = debut_periode.replace(day=1)
    for _ in range(6):
        cle = curseur.strftime('%Y-%m')
        labels_mois.append(curseur.strftime('%b %Y'))
        soumissions_data.append(soumissions_dict.get(cle, 0))
        analyses_data.append(analyses_dict.get(cle, 0))
        curseur = (curseur + timedelta(days=32)).replace(day=1)

    contexte = {
        'stats': stats,
        'labels_mois': json.dumps(labels_mois),
        'soumissions_data': json.dumps(soumissions_data),
        'analyses_data': json.dumps(analyses_data),
    }
    return render(request, 'detection/dashboard_admin.html', contexte)


@login_required
@user_passes_test(est_admin, login_url='detection:dashboard')
def configurer_systeme(request):
    """
    Cas d'usage : Configurer le système.
    Séquence : 31. configurerSysteme(params) → 32. configurationAppliquee()
    """
    config = ConfigurationSysteme.get_config()

    if request.method == 'POST':
        form = ConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuration du système appliquée avec succès.")
            return redirect('detection:configurer_systeme')
    else:
        form = ConfigurationForm(instance=config)

    return render(request, 'detection/configurer_systeme.html', {'form': form, 'config': config})
