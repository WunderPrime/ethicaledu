from django.contrib import admin
from .models import (
    Profil, ConfigurationSysteme, Travail, Analyse, SourceSimilaire, RapportPlagiat
)


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'filiere', 'departement', 'date_creation')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


@admin.register(ConfigurationSysteme)
class ConfigurationSystemeAdmin(admin.ModelAdmin):
    list_display = ('seuil_alerte', 'taille_ngramme', 'algorithme_par_defaut', 'date_maj')


class SourceSimilaireInline(admin.TabularInline):
    model = SourceSimilaire
    extra = 0


@admin.register(Travail)
class TravailAdmin(admin.ModelAdmin):
    list_display = ('titre', 'etudiant', 'statut', 'date_depot')
    list_filter = ('statut',)
    search_fields = ('titre', 'etudiant__username')


@admin.register(Analyse)
class AnalyseAdmin(admin.ModelAdmin):
    list_display = ('travail', 'enseignant', 'taux_plagiat', 'algorithme', 'date_analyse')
    list_filter = ('algorithme',)
    inlines = [SourceSimilaireInline]


@admin.register(RapportPlagiat)
class RapportPlagiatAdmin(admin.ModelAdmin):
    list_display = ('analyse', 'pourcentage', 'date_generation')
