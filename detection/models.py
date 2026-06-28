from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Profil(models.Model):
    """
    Étend le User natif de Django avec un rôle.
    Correspond à la classe abstraite Utilisateur du diagramme de classes,
    spécialisée en Étudiant / Enseignant / Admin via le champ `role`.
    """

    ETUDIANT = 'etudiant'
    ENSEIGNANT = 'enseignant'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (ETUDIANT, 'Étudiant'),
        (ENSEIGNANT, 'Enseignant'),
        (ADMIN, 'Administrateur'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ETUDIANT)

    # Attributs spécifiques Étudiant
    num_etudiant = models.CharField(max_length=50, blank=True, null=True)
    filiere = models.CharField(max_length=100, blank=True, null=True)

    # Attributs spécifiques Enseignant
    departement = models.CharField(max_length=100, blank=True, null=True)
    grade = models.CharField(max_length=100, blank=True, null=True)

    # Attributs spécifiques Admin
    niveau_acces = models.IntegerField(default=1, blank=True, null=True)

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profils"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    def est_etudiant(self):
        return self.role == self.ETUDIANT

    def est_enseignant(self):
        return self.role == self.ENSEIGNANT

    def est_admin(self):
        return self.role == self.ADMIN


class ConfigurationSysteme(models.Model):
    """
    Paramètres globaux configurables par l'Admin.
    Cas d'usage : Configurer le système.
    """
    seuil_alerte = models.FloatField(
        default=30.0,
        help_text="Taux de similarité (%) au-delà duquel un travail est signalé comme suspect."
    )
    taille_ngramme = models.IntegerField(
        default=3,
        help_text="Taille des n-grammes utilisés pour la comparaison de texte."
    )
    algorithme_par_defaut = models.CharField(
        max_length=20,
        choices=[('jaccard', 'Indice de Jaccard'), ('cosinus', 'Similarité cosinus')],
        default='jaccard'
    )
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration du système"
        verbose_name_plural = "Configuration du système"

    def __str__(self):
        return f"Configuration (seuil={self.seuil_alerte}%, algo={self.algorithme_par_defaut})"

    @classmethod
    def get_config(cls):
        """Retourne la configuration unique du système (singleton)."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class Travail(models.Model):
    """
    Représente un travail soumis par un étudiant.
    Cas d'usage : Soumettre un travail.
    """

    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('extrait', 'Texte extrait'),
        ('analyse', 'Analysé'),
        ('erreur', 'Erreur'),
    ]

    titre = models.CharField(max_length=200)
    fichier = models.FileField(upload_to='travaux/%Y/%m/')
    etudiant = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='travaux',
        limit_choices_to={'profil__role': Profil.ETUDIANT}
    )
    date_depot = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    texte_extrait = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Travail"
        verbose_name_plural = "Travaux"
        ordering = ['-date_depot']

    def __str__(self):
        return f"{self.titre} ({self.etudiant.username})"

    def get_extension(self):
        return self.fichier.name.split('.')[-1].lower()

    def get_absolute_url(self):
        return reverse('detection:detail_travail', args=[self.pk])


class Analyse(models.Model):
    """
    Représente une analyse de plagiat lancée sur un Travail.
    Cas d'usage : Analyser le plagiat «include» Comparer avec la BDD.
    """

    ALGO_CHOICES = [
        ('jaccard', 'Indice de Jaccard'),
        ('cosinus', 'Similarité cosinus'),
    ]

    travail = models.OneToOneField(Travail, on_delete=models.CASCADE, related_name='analyse')
    enseignant = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='analyses_lancees',
        limit_choices_to={'profil__role': Profil.ENSEIGNANT}
    )
    taux_plagiat = models.FloatField(default=0.0)
    date_analyse = models.DateTimeField(auto_now_add=True)
    algorithme = models.CharField(max_length=20, choices=ALGO_CHOICES, default='jaccard')

    class Meta:
        verbose_name = "Analyse"
        verbose_name_plural = "Analyses"
        ordering = ['-date_analyse']

    def __str__(self):
        return f"Analyse de {self.travail.titre} — {self.taux_plagiat:.1f}%"


class SourceSimilaire(models.Model):
    """
    Une source détectée comme similaire lors d'une Analyse.
    Permet de modéliser comparerBDD() / comparerSources() -> List.
    """
    analyse = models.ForeignKey(Analyse, on_delete=models.CASCADE, related_name='sources')
    travail_source = models.ForeignKey(
        Travail, on_delete=models.CASCADE, related_name='cite_comme_source'
    )
    score_similarite = models.FloatField()

    class Meta:
        verbose_name = "Source similaire"
        verbose_name_plural = "Sources similaires"
        ordering = ['-score_similarite']

    def __str__(self):
        return f"{self.travail_source.titre} — {self.score_similarite:.1f}%"


class RapportPlagiat(models.Model):
    """
    Rapport détaillé généré à partir d'une Analyse.
    Hérite conceptuellement de Rapport (genererPDF, afficherSimilitudes)
    et ajoute mettreEnEvidencePassages().
    Cas d'usage : Générer un rapport détaillé «include» Mettre en évidence les passages.
    """
    analyse = models.OneToOneField(Analyse, on_delete=models.CASCADE, related_name='rapport')
    date_generation = models.DateTimeField(auto_now_add=True)
    pourcentage = models.FloatField()
    passages_similaires = models.JSONField(
        default=list, blank=True,
        help_text="Liste des passages similaires détectés : [{texte, source, score}, ...]"
    )
    contenu_resume = models.TextField(blank=True)

    class Meta:
        verbose_name = "Rapport de plagiat"
        verbose_name_plural = "Rapports de plagiat"
        ordering = ['-date_generation']

    def __str__(self):
        return f"Rapport — {self.analyse.travail.titre} ({self.pourcentage:.1f}%)"

    def get_absolute_url(self):
        return reverse('detection:detail_rapport', args=[self.pk])
