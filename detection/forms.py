from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Travail, Profil, ConfigurationSysteme


class InscriptionForm(UserCreationForm):
    """Formulaire d'inscription, avec choix du rôle (Étudiant ou Enseignant)."""

    role = forms.ChoiceField(
        choices=[(Profil.ETUDIANT, 'Étudiant'), (Profil.ENSEIGNANT, 'Enseignant')],
        label="Je suis",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    email = forms.EmailField(
        required=True, label="Adresse e-mail",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    num_etudiant = forms.CharField(
        required=False, label="Numéro étudiant",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    filiere = forms.CharField(
        required=False, label="Filière",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    departement = forms.CharField(
        required=False, label="Département",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    grade = forms.CharField(
        required=False, label="Grade",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom_champ in ('username', 'first_name', 'last_name', 'password1', 'password2'):
            self.fields[nom_champ].widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        user = super().save(commit=commit)
        role = self.cleaned_data['role']
        Profil.objects.create(
            user=user,
            role=role,
            num_etudiant=self.cleaned_data.get('num_etudiant') or None,
            filiere=self.cleaned_data.get('filiere') or None,
            departement=self.cleaned_data.get('departement') or None,
            grade=self.cleaned_data.get('grade') or None,
        )
        return user


class SoumissionTravailForm(forms.ModelForm):
    """Formulaire de soumission d'un travail par l'étudiant."""

    class Meta:
        model = Travail
        fields = ['titre', 'fichier']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre du travail'}),
            'fichier': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        if fichier:
            extension = fichier.name.split('.')[-1].lower()
            if extension not in ('pdf', 'docx', 'txt'):
                raise forms.ValidationError(
                    "Seuls les fichiers PDF, DOCX et TXT sont acceptés."
                )
        return fichier


class LancerAnalyseForm(forms.Form):
    """Formulaire de lancement d'une analyse de plagiat par l'enseignant."""

    algorithme = forms.ChoiceField(
        choices=[('jaccard', 'Indice de Jaccard'), ('cosinus', 'Similarité cosinus')],
        initial='jaccard',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ConfigurationForm(forms.ModelForm):
    """Formulaire de configuration du système, réservé à l'Admin."""

    class Meta:
        model = ConfigurationSysteme
        fields = ['seuil_alerte', 'taille_ngramme', 'algorithme_par_defaut']
        widgets = {
            'seuil_alerte': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'taille_ngramme': forms.NumberInput(attrs={'class': 'form-control'}),
            'algorithme_par_defaut': forms.Select(attrs={'class': 'form-select'}),
        }


class GestionUtilisateurForm(forms.ModelForm):
    """Formulaire de création/édition d'un utilisateur par Admin ou Enseignant."""

    role = forms.ChoiceField(choices=Profil.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    password = forms.CharField(
        required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Laisser vide pour ne pas modifier le mot de passe."
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            role = self.cleaned_data['role']
            Profil.objects.update_or_create(user=user, defaults={'role': role})
        return user
