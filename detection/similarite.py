"""
Module Analyse — correspond à la classe Analyse du diagramme de classes.
Méthodes : analyser(travail), comparerSources(), calculerTaux(), comparerBDD(travail)

Principe technique (sans IA), conforme au sujet :
- découpage du texte en n-grammes
- comparaison par indice de Jaccard ou similarité cosinus simple
- détection des passages identiques
"""
import math
import re
from collections import Counter


def decouper_en_ngrammes(texte, n=3):
    """Découpe un texte en n-grammes de mots (ensemble de tuples)."""
    mots = texte.split()
    if len(mots) < n:
        return {tuple(mots)} if mots else set()
    return {tuple(mots[i:i + n]) for i in range(len(mots) - n + 1)}


def similarite_jaccard(texte_a, texte_b, n=3):
    """
    Indice de Jaccard = |A ∩ B| / |A ∪ B|
    Retourne un taux de similarité en pourcentage (0-100).
    """
    ngrammes_a = decouper_en_ngrammes(texte_a, n)
    ngrammes_b = decouper_en_ngrammes(texte_b, n)

    if not ngrammes_a or not ngrammes_b:
        return 0.0

    intersection = ngrammes_a & ngrammes_b
    union = ngrammes_a | ngrammes_b

    if not union:
        return 0.0

    return (len(intersection) / len(union)) * 100


def vecteur_frequence(texte):
    """Construit un vecteur de fréquence de mots (sac de mots)."""
    mots = re.findall(r'\w+', texte.lower())
    return Counter(mots)


def similarite_cosinus(texte_a, texte_b):
    """
    Similarité cosinus simple entre deux sacs de mots.
    cos(θ) = (A · B) / (||A|| * ||B||)
    Retourne un taux de similarité en pourcentage (0-100).
    """
    vec_a = vecteur_frequence(texte_a)
    vec_b = vecteur_frequence(texte_b)

    mots_communs = set(vec_a.keys()) & set(vec_b.keys())
    produit_scalaire = sum(vec_a[mot] * vec_b[mot] for mot in mots_communs)

    norme_a = math.sqrt(sum(val ** 2 for val in vec_a.values()))
    norme_b = math.sqrt(sum(val ** 2 for val in vec_b.values()))

    if norme_a == 0 or norme_b == 0:
        return 0.0

    cosinus = produit_scalaire / (norme_a * norme_b)
    return round(cosinus * 100, 2)


def detecter_passages_similaires(texte_a, texte_b, n=8, seuil_phrase=0.6):
    """
    Détecte des passages (séquences de n mots) communs ou très proches
    entre deux textes, pour la mise en évidence dans le rapport.
    Retourne une liste de passages : [{"texte": ..., "position": ...}, ...]
    """
    mots_a = texte_a.split()
    ngrammes_a = [
        (" ".join(mots_a[i:i + n]), i)
        for i in range(0, max(len(mots_a) - n + 1, 0))
    ]

    ngrammes_b_set = decouper_en_ngrammes(texte_b, n)

    passages = []
    for phrase, position in ngrammes_a:
        tuple_phrase = tuple(phrase.split())
        if tuple_phrase in ngrammes_b_set:
            passages.append({"texte": phrase, "position": position})

    return passages


def calculer_taux(texte_a, texte_b, algorithme='jaccard', n=3):
    """
    Point d'entrée principal du calcul de taux de similarité.
    Correspond à la méthode calculerTaux() du diagramme de classes.
    """
    if algorithme == 'cosinus':
        return similarite_cosinus(texte_a, texte_b)
    return similarite_jaccard(texte_a, texte_b, n=n)


def comparer_avec_corpus(texte_cible, liste_travaux, algorithme='jaccard', n=3):
    """
    Correspond à comparerBDD(travail) / comparerSources().
    Compare un texte avec une liste de Travail (BDD) et retourne
    les scores triés par similarité décroissante.

    `liste_travaux` : queryset ou liste d'objets Travail avec texte_extrait rempli.
    Retourne une liste de tuples (travail, score).
    """
    resultats = []
    for travail in liste_travaux:
        if not travail.texte_extrait:
            continue
        score = calculer_taux(texte_cible, travail.texte_extrait, algorithme=algorithme, n=n)
        resultats.append((travail, score))

    resultats.sort(key=lambda x: x[1], reverse=True)
    return resultats
