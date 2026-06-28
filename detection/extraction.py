"""
Module Extraction — correspond à la classe Extraction du diagramme de classes.
Méthodes : extraireTexte(fichier), parserPDF(), parserDOCX()
"""
import os
import re

import PyPDF2
from docx import Document as DocxDocument


def parser_pdf(chemin_fichier):
    """Extrait le texte brut d'un fichier PDF."""
    texte = []
    with open(chemin_fichier, 'rb') as f:
        lecteur = PyPDF2.PdfReader(f)
        for page in lecteur.pages:
            contenu = page.extract_text()
            if contenu:
                texte.append(contenu)
    return "\n".join(texte)


def parser_docx(chemin_fichier):
    """Extrait le texte brut d'un fichier DOCX."""
    doc = DocxDocument(chemin_fichier)
    paragraphes = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphes)


def extraire_texte(chemin_fichier):
    """
    Point d'entrée principal de l'extraction.
    Détecte le type de fichier et appelle le parseur adéquat.
    """
    extension = os.path.splitext(chemin_fichier)[1].lower()

    if extension == '.pdf':
        texte = parser_pdf(chemin_fichier)
    elif extension in ('.docx',):
        texte = parser_docx(chemin_fichier)
    elif extension == '.txt':
        with open(chemin_fichier, 'r', encoding='utf-8', errors='ignore') as f:
            texte = f.read()
    else:
        raise ValueError(f"Format de fichier non supporté : {extension}")

    return nettoyer_texte(texte)


def nettoyer_texte(texte):
    """Normalise le texte extrait : espaces, casse, ponctuation superflue."""
    texte = texte.lower()
    texte = re.sub(r'\s+', ' ', texte)
    texte = texte.strip()
    return texte
