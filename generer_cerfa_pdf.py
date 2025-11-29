#!/usr/bin/env python3
"""
GÉNÉRATION PDF CERFA - SCI Soeurise
===================================
Génère des PDF pré-remplis pour les formulaires fiscaux :
- 2065 : Déclaration de résultats
- 2033-A : Bilan simplifié
- 2033-B : Compte de résultat simplifié
- 2033-F : Composition du capital

Usage:
    python generer_cerfa_pdf.py [fichier_json]

Exemple:
    python generer_cerfa_pdf.py cerfa_2024_20251121_161612.json
"""

import sys
import os
import json
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# ==============================================================================
# STYLES
# ==============================================================================

def get_styles():
    """Retourne les styles personnalisés"""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='TitrePrincipal',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#1a365d')
    ))

    styles.add(ParagraphStyle(
        name='SousTitre',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.HexColor('#2c5282')
    ))

    styles.add(ParagraphStyle(
        name='Section',
        parent=styles['Heading3'],
        fontSize=11,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#2b6cb0'),
        borderWidth=1,
        borderColor=colors.HexColor('#bee3f8'),
        borderPadding=5,
        backColor=colors.HexColor('#ebf8ff')
    ))

    styles.add(ParagraphStyle(
        name='Info',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.gray
    ))

    return styles


def format_montant(montant):
    """Formate un montant en euros (entier, sans centimes)"""
    if montant is None:
        return "-"
    try:
        val = float(montant)
        if val == 0:
            return "-"
        # Arrondi à l'euro, pas de centimes
        val_arrondie = int(round(val))
        # Format avec espaces comme séparateurs de milliers
        return f"{val_arrondie:,} €".replace(",", " ")
    except:
        return str(montant)


# ==============================================================================
# PAGE 2065 - DÉCLARATION DE RÉSULTATS
# ==============================================================================

def generer_page_2065(data, styles):
    """Génère la page 2065 - Déclaration de résultats"""
    elements = []

    societe = data.get("meta", {}).get("societe", {})
    form_2065 = data.get("formulaires", {}).get("2065", {})
    exercice = form_2065.get("exercice", {})

    # En-tête
    elements.append(Paragraph("CERFA N° 2065", styles['TitrePrincipal']))
    elements.append(Paragraph("IMPÔT SUR LES SOCIÉTÉS", styles['SousTitre']))
    elements.append(Paragraph("Déclaration de résultats", styles['SousTitre']))
    elements.append(Spacer(1, 10))

    # Identification
    elements.append(Paragraph("IDENTIFICATION DE LA SOCIÉTÉ", styles['Section']))

    info_data = [
        ["Dénomination", societe.get("denomination", "")],
        ["Forme juridique", societe.get("forme_juridique", "")],
        ["SIRET", societe.get("siret", "")],
        ["Adresse", f"{societe.get('adresse', '')} {societe.get('code_postal', '')} {societe.get('ville', '')}"],
        ["Activité", societe.get("activite", "")],  # Texte complet, pas de troncature
        ["Régime fiscal", societe.get("regime_fiscal", "")],
    ]

    table = Table(info_data, colWidths=[5*cm, 12*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e2e8f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 15))

    # Exercice
    elements.append(Paragraph("EXERCICE", styles['Section']))

    exercice_data = [
        ["Année", str(exercice.get("annee", ""))],
        ["Date début", exercice.get("date_debut", "")],
        ["Date fin", exercice.get("date_fin", "")],
    ]

    table = Table(exercice_data, colWidths=[5*cm, 12*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 15))

    # Résultat fiscal
    elements.append(Paragraph("RÉSULTAT FISCAL ET IMPÔT", styles['Section']))

    resultat_data = [
        ["Description", "Montant"],
        ["Résultat comptable", format_montant(form_2065.get("resultat_comptable"))],
        ["Déficit reportable utilisé", format_montant(form_2065.get("deficit_reportable_utilise"))],
        ["Résultat fiscal imposable", format_montant(form_2065.get("resultat_fiscal"))],
        ["IS taux réduit (15%)", format_montant(form_2065.get("is_taux_reduit_15"))],
        ["IS taux normal (25%)", format_montant(form_2065.get("is_taux_normal_25"))],
        ["IS TOTAL À PAYER", format_montant(form_2065.get("is_total"))],
        ["Résultat net après IS", format_montant(form_2065.get("resultat_net_apres_is"))],
        ["Nouveau déficit reportable", format_montant(form_2065.get("nouveau_deficit_reportable"))],
    ]

    table = Table(resultat_data, colWidths=[10*cm, 7*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#fed7d7')),
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#c6f6d5')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)

    return elements


# ==============================================================================
# PAGE 2033-A - BILAN
# ==============================================================================

def generer_page_2033a(data, styles):
    """Génère la page 2033-A - Bilan"""
    elements = []

    societe = data.get("meta", {}).get("societe", {})
    form_2033a = data.get("formulaires", {}).get("2033-A", {})
    actif = form_2033a.get("actif", {})
    passif = form_2033a.get("passif", {})

    # En-tête
    elements.append(Paragraph("CERFA N° 2033-A", styles['TitrePrincipal']))
    elements.append(Paragraph("BILAN SIMPLIFIÉ", styles['SousTitre']))
    elements.append(Paragraph(f"{societe.get('denomination', '')} - SIRET {societe.get('siret', '')}", styles['Info']))
    elements.append(Spacer(1, 15))

    # ACTIF
    elements.append(Paragraph("ACTIF", styles['Section']))

    actif_lignes = [
        ["Case", "Libellé", "Montant"],
        ["", "ACTIF IMMOBILISÉ", ""],
        ["AB", "Terrains", format_montant(actif.get("AB", {}).get("montant"))],
        ["AC", "Constructions", format_montant(actif.get("AC", {}).get("montant"))],
        ["AG", "Participations et titres immobilisés", format_montant(actif.get("AG", {}).get("montant"))],
        ["AH2", "Provisions pour dépréciation (en déduction)", format_montant(actif.get("AH2", {}).get("montant"))],
        ["AI", "TOTAL ACTIF IMMOBILISÉ NET", format_montant(actif.get("AI", {}).get("montant"))],
        ["", "ACTIF CIRCULANT", ""],
        ["AN", "Créances clients et comptes rattachés", format_montant(actif.get("AN", {}).get("montant"))],
        ["AP", "Valeurs mobilières de placement", format_montant(actif.get("AP", {}).get("montant"))],
        ["AQ", "Disponibilités", format_montant(actif.get("AQ", {}).get("montant"))],
        ["AS", "TOTAL ACTIF CIRCULANT", format_montant(actif.get("AS", {}).get("montant"))],
        ["AT", "TOTAL GÉNÉRAL ACTIF", format_montant(actif.get("AT", {}).get("montant"))],
    ]

    table = Table(actif_lignes, colWidths=[2*cm, 10*cm, 5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e2e8f0')),  # ACTIF IMMOBILISÉ
        ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor('#fee2e2')),  # Provisions (rouge léger)
        ('BACKGROUND', (0, 7), (-1, 7), colors.HexColor('#e2e8f0')),  # ACTIF CIRCULANT
        ('BACKGROUND', (0, 8), (-1, 8), colors.HexColor('#bee3f8')),  # TOTAL ACTIF IMMOBILISÉ
        ('BACKGROUND', (0, 11), (-1, 11), colors.HexColor('#bee3f8')),  # TOTAL ACTIF CIRCULANT
        ('BACKGROUND', (0, 12), (-1, 12), colors.HexColor('#c6f6d5')),  # TOTAL GÉNÉRAL
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),  # Provisions en gras
        ('FONTNAME', (0, 7), (-1, 7), 'Helvetica-Bold'),
        ('FONTNAME', (0, 8), (-1, 8), 'Helvetica-Bold'),
        ('FONTNAME', (0, 11), (-1, 11), 'Helvetica-Bold'),
        ('FONTNAME', (0, 12), (-1, 12), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 15))

    # PASSIF
    elements.append(Paragraph("PASSIF", styles['Section']))

    passif_lignes = [
        ["Case", "Libellé", "Montant"],
        ["", "CAPITAUX PROPRES", ""],
        ["BA", "Capital social", format_montant(passif.get("BA", {}).get("montant"))],
        ["BF", "Report à nouveau", format_montant(passif.get("BF", {}).get("montant"))],
        ["BG", "Résultat de l'exercice", format_montant(passif.get("BG", {}).get("montant"))],
        ["BJ", "TOTAL CAPITAUX PROPRES", format_montant(passif.get("BJ", {}).get("montant"))],
        ["BK", "Provisions pour risques et charges", format_montant(passif.get("BK", {}).get("montant"))],
        ["", "DETTES", ""],
        ["BL", "Emprunts et dettes financières", format_montant(passif.get("BL", {}).get("montant"))],
        ["BO", "Dettes fournisseurs", format_montant(passif.get("BO", {}).get("montant"))],
        ["BR", "Autres dettes (comptes courants associés)", format_montant(passif.get("BR", {}).get("montant"))],
        ["BT", "TOTAL DETTES", format_montant(passif.get("BT", {}).get("montant"))],
        ["BU", "TOTAL GÉNÉRAL PASSIF", format_montant(passif.get("BU", {}).get("montant"))],
    ]

    table = Table(passif_lignes, colWidths=[2*cm, 10*cm, 5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 7), (-1, 7), colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#bee3f8')),
        ('BACKGROUND', (0, 11), (-1, 11), colors.HexColor('#bee3f8')),
        ('BACKGROUND', (0, 12), (-1, 12), colors.HexColor('#c6f6d5')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        ('FONTNAME', (0, 7), (-1, 7), 'Helvetica-Bold'),
        ('FONTNAME', (0, 11), (-1, 11), 'Helvetica-Bold'),
        ('FONTNAME', (0, 12), (-1, 12), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)

    return elements


# ==============================================================================
# PAGE 2033-B - COMPTE DE RÉSULTAT
# ==============================================================================

def generer_page_2033b(data, styles):
    """Génère la page 2033-B - Compte de résultat"""
    elements = []

    societe = data.get("meta", {}).get("societe", {})
    form_2033b = data.get("formulaires", {}).get("2033-B", {})

    # En-tête
    elements.append(Paragraph("CERFA N° 2033-B", styles['TitrePrincipal']))
    elements.append(Paragraph("COMPTE DE RÉSULTAT SIMPLIFIÉ", styles['SousTitre']))
    elements.append(Paragraph(f"{societe.get('denomination', '')} - SIRET {societe.get('siret', '')}", styles['Info']))
    elements.append(Spacer(1, 15))

    # Charges d'exploitation
    elements.append(Paragraph("CHARGES D'EXPLOITATION", styles['Section']))

    charges_data = [
        ["Case", "Libellé", "Montant"],
        ["FM", "Autres achats et charges externes", format_montant(form_2033b.get("FM", {}).get("montant"))],
        ["FN", "Impôts, taxes et versements assimilés", format_montant(form_2033b.get("FN", {}).get("montant"))],
        ["FQ", "Dotations aux amortissements", format_montant(form_2033b.get("FQ", {}).get("montant"))],
        ["FU", "TOTAL CHARGES D'EXPLOITATION", format_montant(form_2033b.get("FU", {}).get("montant"))],
    ]

    table = Table(charges_data, colWidths=[2*cm, 10*cm, 5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c53030')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#fed7d7')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    # Résultat d'exploitation
    elements.append(Paragraph("RÉSULTAT D'EXPLOITATION", styles['Section']))

    res_exp_data = [
        ["Case", "Libellé", "Montant"],
        ["FV", "Résultat d'exploitation (Produits - Charges)", format_montant(form_2033b.get("FV", {}).get("montant"))],
    ]

    table = Table(res_exp_data, colWidths=[2*cm, 10*cm, 5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    # Produits financiers
    elements.append(Paragraph("PRODUITS FINANCIERS", styles['Section']))

    produits_fin_data = [
        ["Case", "Libellé", "Montant"],
        ["GA", "Produits financiers de participations", format_montant(form_2033b.get("GA", {}).get("montant"))],
        ["GC", "Autres intérêts et produits assimilés", format_montant(form_2033b.get("GC", {}).get("montant"))],
        ["GG", "TOTAL PRODUITS FINANCIERS", format_montant(form_2033b.get("GG", {}).get("montant"))],
    ]

    table = Table(produits_fin_data, colWidths=[2*cm, 10*cm, 5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f855a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#c6f6d5')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    # Charges financières
    elements.append(Paragraph("CHARGES FINANCIÈRES", styles['Section']))

    charges_fin_data = [
        ["Case", "Libellé", "Montant"],
        ["GI", "Intérêts et charges assimilées", format_montant(form_2033b.get("GI", {}).get("montant"))],
        ["GL", "TOTAL CHARGES FINANCIÈRES", format_montant(form_2033b.get("GL", {}).get("montant"))],
    ]

    table = Table(charges_fin_data, colWidths=[2*cm, 10*cm, 5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c53030')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fed7d7')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    # Résultat financier et courant
    elements.append(Paragraph("RÉSULTATS", styles['Section']))

    resultats_data = [
        ["Case", "Libellé", "Montant"],
        ["GM", "Résultat financier", format_montant(form_2033b.get("GM", {}).get("montant"))],
        ["GN", "Résultat courant avant impôts", format_montant(form_2033b.get("GN", {}).get("montant"))],
        ["HL", "BÉNÉFICE OU PERTE", format_montant(form_2033b.get("HL", {}).get("montant"))],
    ]

    table = Table(resultats_data, colWidths=[2*cm, 10*cm, 5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#c6f6d5')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)

    return elements


# ==============================================================================
# PAGE 2033-F - COMPOSITION DU CAPITAL
# ==============================================================================

def generer_page_2033f(data, styles):
    """Génère la page 2033-F - Composition du capital"""
    elements = []

    societe = data.get("meta", {}).get("societe", {})
    form_2033f = data.get("formulaires", {}).get("2033-F", {})

    # En-tête
    elements.append(Paragraph("CERFA N° 2033-F", styles['TitrePrincipal']))
    elements.append(Paragraph("COMPOSITION DU CAPITAL SOCIAL", styles['SousTitre']))
    elements.append(Paragraph(f"{societe.get('denomination', '')} - SIRET {societe.get('siret', '')}", styles['Info']))
    elements.append(Spacer(1, 15))

    # Capital
    elements.append(Paragraph("CAPITAL SOCIAL", styles['Section']))

    capital_data = [
        ["Description", "Valeur"],
        ["Capital social", format_montant(form_2033f.get("capital_social"))],
        ["Nombre de parts", str(form_2033f.get("nombre_parts", ""))],
        ["Valeur nominale", format_montant(form_2033f.get("valeur_nominale"))],
    ]

    table = Table(capital_data, colWidths=[10*cm, 7*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 15))

    # Associés
    elements.append(Paragraph("RÉPARTITION ENTRE ASSOCIÉS", styles['Section']))

    associes = form_2033f.get("associes", [])
    associes_data = [["Nom", "Parts", "Pourcentage", "Adresse"]]

    for associe in associes:
        associes_data.append([
            associe.get("nom", ""),
            str(associe.get("parts", "")),
            f"{associe.get('pourcentage', '')} %",
            associe.get("adresse", "")[:30] + "..." if len(associe.get("adresse", "")) > 30 else associe.get("adresse", "")
        ])

    table = Table(associes_data, colWidths=[4*cm, 2*cm, 2.5*cm, 8.5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 15))

    # Gérant
    elements.append(Paragraph("GÉRANT", styles['Section']))

    gerant = societe.get("gerant", {})
    if isinstance(gerant, dict):
        gerant_data = [
            ["Nom", f"{gerant.get('prenom', '')} {gerant.get('nom', '')}"],
            ["Date de naissance", gerant.get("date_naissance", "")],
            ["Lieu de naissance", gerant.get("lieu_naissance", "")],
            ["Nationalité", gerant.get("nationalite", "")],
            ["Adresse", gerant.get("adresse", "")],
        ]
    else:
        gerant_data = [["Gérant", str(gerant)]]

    table = Table(gerant_data, colWidths=[5*cm, 12*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
    ]))
    elements.append(table)

    return elements


# ==============================================================================
# GÉNÉRATION PRINCIPALE
# ==============================================================================

def generer_pdf(json_file):
    """Génère le PDF complet à partir du fichier JSON"""

    # Charger les données
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    annee = data.get("meta", {}).get("exercice", "")
    societe = data.get("meta", {}).get("societe", {}).get("denomination", "")

    # Nom du fichier PDF
    pdf_file = json_file.replace('.json', '.pdf')

    print("=" * 70)
    print(f"GÉNÉRATION PDF CERFA - {societe} - {annee}")
    print("=" * 70)

    # Créer le document
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    styles = get_styles()
    elements = []

    # Page 2065
    print("  Génération 2065 (Déclaration de résultats)...")
    elements.extend(generer_page_2065(data, styles))
    elements.append(PageBreak())

    # Page 2033-A
    print("  Génération 2033-A (Bilan)...")
    elements.extend(generer_page_2033a(data, styles))
    elements.append(PageBreak())

    # Page 2033-B
    print("  Génération 2033-B (Compte de résultat)...")
    elements.extend(generer_page_2033b(data, styles))
    elements.append(PageBreak())

    # Page 2033-F
    print("  Génération 2033-F (Composition capital)...")
    elements.extend(generer_page_2033f(data, styles))

    # Pied de page avec date de génération
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')} - _Head.Soeurise",
        styles['Info']
    ))

    # Construire le PDF
    doc.build(elements)

    print("-" * 70)
    print(f"PDF généré : {pdf_file}")
    print("=" * 70)

    return pdf_file


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Chercher le fichier JSON le plus récent
        import glob
        json_files = glob.glob("cerfa_*.json")
        if json_files:
            json_file = max(json_files, key=os.path.getmtime)
            print(f"Utilisation du fichier le plus récent : {json_file}")
        else:
            print("Usage: python generer_cerfa_pdf.py <fichier_json>")
            print("Exemple: python generer_cerfa_pdf.py cerfa_2024_20251121_161612.json")
            sys.exit(1)
    else:
        json_file = sys.argv[1]

    if not os.path.exists(json_file):
        print(f"Erreur: Fichier non trouvé: {json_file}")
        sys.exit(1)

    generer_pdf(json_file)
