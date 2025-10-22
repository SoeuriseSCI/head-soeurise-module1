"""
MODULE 2 WORKFLOW BRANCHES V2 - LES 3 BRANCHES DE TRAITEMENT (FIXED)
=============================================================

Branche 1: Événements simples (loyer/charge)
Branche 2: Initialisation bilan 2023
Branche 3: Clôture exercice 2023

Rôle: Encapsuler la logique spécifique à chaque type d'événement
Gère aussi: Envoi d'emails Markdown, parsing JSON depuis Markdown

FIX: Corriger EnvoyeurMarkdown pour accepter email_to et attacher Markdown
"""

import json
import re
import smtplib
import os
import tempfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session
from models_module2 import EvenementComptable


# ═══════════════════════════════════════════════════════════════════════════════
# 1. BRANCHE ÉVÉNEMENT SIMPLE
# ═══════════════════════════════════════════════════════════════════════════════

class BrancheEvenementSimple:
    """Gère les événements simples: loyer, charge, etc."""
    
    @staticmethod
    def detecter_evenements(body: str) -> List[Dict]:
        """Détecte les événements comptables dans le body"""
        
        events = []
        
        # Patterns pour loyers
        if any(kw in body.lower() for kw in ['loyer', 'location', 'paiement locataire', 'encaissement']):
            events.append({
                'type': 'LOYER',
                'keywords': ['loyer', 'location', 'encaissement']
            })
        
        # Patterns pour charges entretien
        if any(kw in body.lower() for kw in ['entretien', 'réparation', 'reparation', 'maintenance']):
            events.append({
                'type': 'CHARGE_ENTRETIEN',
                'keywords': ['entretien', 'réparation']
            })
        
        # Patterns pour assurances
        if any(kw in body.lower() for kw in ['assurance', 'prime', 'police']):
            events.append({
                'type': 'ASSURANCE',
                'keywords': ['assurance']
            })
        
        # Patterns pour taxes
        if any(kw in body.lower() for kw in ['taxe foncière', 'impôt', 'tf']):
            events.append({
                'type': 'TAXE',
                'keywords': ['taxe', 'impôt']
            })
        
        # Patterns pour charges copropriété
        if any(kw in body.lower() for kw in ['copropriété', 'syndic', 'charges communes']):
            events.append({
                'type': 'CHARGE_COPROPRIETE',
                'keywords': ['copropriété', 'syndic']
            })
        
        return events
    
    @staticmethod
    def extraire_montant(text: str) -> Optional[float]:
        """Extrait le montant principal du texte"""
        
        # Pattern avec €: "1000€" ou "1 000€" ou "1000,50€"
        pattern_euro = r'(\d{1,3}(?:\s?\d{3})*(?:[.,]\d{2})?)\s?€'
        match = re.search(pattern_euro, text)
        if match:
            montant_str = match.group(1).replace(' ', '').replace(',', '.')
            try:
                return float(montant_str)
            except ValueError:
                pass
        
        # Pattern sans €: "1000" ou "1000.50" (nombre seul)
        pattern_num = r'(\d{3,}(?:[.,]\d{2})?)'
        matches = re.findall(pattern_num, text)
        if matches:
            # Prendre le plus grand nombre trouvé
            montants = []
            for m in matches:
                try:
                    montants.append(float(m.replace(',', '.')))
                except ValueError:
                    pass
            
            if montants:
                return max(montants)
        
        return None
    
    def traiter(self, email: Dict, session: Session) -> Dict:
        """Traite un événement simple et crée EvenementComptable"""
        
        try:
            body = email.get('body', '')
            
            # Détecter événements
            events = self.detecter_evenements(body)
            if not events:
                return {
                    "statut": "ERREUR",
                    "message": "Aucun événement détecté"
                }
            
            # Extraire montant
            montant = self.extraire_montant(body)
            if not montant:
                return {
                    "statut": "ERREUR",
                    "message": "Impossible d'extraire le montant"
                }
            
            # Créer EvenementComptable EN_ATTENTE
            evt = EvenementComptable(
                email_id=email.get('email_id'),
                email_from=email.get('from'),
                email_subject=email.get('subject', ''),
                email_body=body[:1000],  # Limiter à 1000 chars
                type_evenement=events[0]['type'],
                est_comptable=True,
                statut='EN_ATTENTE',
                propositions_json=json.dumps({
                    "type": events[0]['type'],
                    "montant": montant
                })
            )
            
            session.add(evt)
            session.commit()
            
            return {
                "statut": "OK",
                "message": f"EvenementComptable créé: {events[0]['type']} - {montant}€",
                "evt_id": evt.id,
                "type_evt": events[0]['type'],
                "montant": montant
            }
        
        except Exception as e:
            session.rollback()
            return {
                "statut": "ERREUR",
                "message": f"Erreur traitement: {str(e)[:100]}"
            }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. BRANCHE INIT BILAN 2023
# ═══════════════════════════════════════════════════════════════════════════════

class BrancheInitBilan2023:
    """Gère l'initialisation du bilan 2023"""
    
    def traiter(self, email: Dict, session: Session, workflow) -> Dict:
        """Traite initialisation bilan 2023"""
        
        try:
            # Récupérer les attachments PDF
            attachments = email.get('attachments', [])
            pdf_files = [a for a in attachments if a.get('content_type') == 'application/pdf']
            
            if not pdf_files:
                return {
                    "statut": "ERREUR",
                    "message": "Aucun PDF trouvé"
                }
            
            # Traiter via workflow
            result = workflow._traiter_init_bilan_2023(email)
            
            if result['statut'] != 'OK':
                return result
            
            # Créer EvenementComptable EN_ATTENTE_VALIDATION
            evt = EvenementComptable(
                email_id=email.get('email_id'),
                email_from=email.get('from'),
                email_subject=email.get('subject', ''),
                email_body=email.get('body', '')[:1000],
                type_evenement='INIT_BILAN_2023',
                est_comptable=True,
                statut='EN_ATTENTE_VALIDATION',
                propositions_json=json.dumps(result['propositions'])
            )
            
            session.add(evt)
            session.commit()
            
            return {
                "statut": "OK",
                "message": f"Propositions bilan 2023 générées ({len(result['propositions']['propositions'])} écritures)",
                "evt_id": evt.id,
                "markdown": result['markdown'],
                "token": result['token']
            }
        
        except Exception as e:
            session.rollback()
            return {
                "statut": "ERREUR",
                "message": f"Erreur traitement bilan: {str(e)[:100]}"
            }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. BRANCHE CLÔTURE 2023
# ═══════════════════════════════════════════════════════════════════════════════

class BrancheCloture2023:
    """Gère la clôture de l'exercice 2023"""
    
    def traiter(self, email: Dict, session: Session, workflow) -> Dict:
        """Traite clôture 2023"""
        
        try:
            # Traiter via workflow
            result = workflow._traiter_cloture_2023(email)
            
            if result['statut'] != 'OK':
                return result
            
            # Créer EvenementComptable EN_ATTENTE_VALIDATION
            evt = EvenementComptable(
                email_id=email.get('email_id'),
                email_from=email.get('from'),
                email_subject=email.get('subject', ''),
                email_body=email.get('body', '')[:1000],
                type_evenement='CLOTURE_EXERCICE',
                est_comptable=True,
                statut='EN_ATTENTE_VALIDATION',
                propositions_json=json.dumps(result['propositions'])
            )
            
            session.add(evt)
            session.commit()
            
            return {
                "statut": "OK",
                "message": f"Propositions clôture 2023 générées ({len(result['propositions']['propositions'])} écritures)",
                "evt_id": evt.id,
                "markdown": result['markdown'],
                "token": result['token']
            }
        
        except Exception as e:
            session.rollback()
            return {
                "statut": "ERREUR",
                "message": f"Erreur traitement clôture: {str(e)[:100]}"
            }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ENVOYEUR MARKDOWN (FIXED - Attache le Markdown en pièce jointe)
# ═══════════════════════════════════════════════════════════════════════════════

class EnvoyeurMarkdown:
    """Envoie les propositions par email en Markdown formaté + pièce jointe"""
    
    def __init__(self, email_from: str, email_password: str, email_to: str = None):
        self.email_from = email_from
        self.email_password = email_password
        self.email_to = email_to
    
    def envoyer_propositions(
        self,
        email_to: str,
        type_evt: str,
        markdown: str,
        token: str,
        subject_suffix: str = ""
    ) -> bool:
        """
        Envoie les propositions à Ulrik pour validation
        
        ✅ FIX: Accepte email_to, subject_suffix, attache Markdown
        
        Sujet: [_Head] PROPOSITIONS - Type d'événement [suffix]
        Body: JSON avec token + instructions
        Pièce jointe: Markdown avec propositions
        
        Instructions: Tag [_Head] VALIDE: dans la réponse pour valider
        """
        
        try:
            msg = MIMEMultipart('mixed')
            msg['Subject'] = f"[_Head] PROPOSITIONS - {type_evt} {subject_suffix}".strip()
            msg['From'] = self.email_from
            msg['To'] = email_to
            
            # 1. BODY TEXTE: JSON + Token + Instructions
            
            body_text = f"""
Propositions comptables pour validation

**Type d'événement:** {type_evt}
**Date de génération:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
**Token MD5 de sécurité:** {token}

---

## STRUCTURE JSON DES PROPOSITIONS

```json
{json.dumps(
    {
        "type_evenement": type_evt,
        "token": token,
        "generee_at": datetime.now().isoformat()
    },
    indent=2
)}
```

---

## INSTRUCTIONS POUR VALIDATION

1. **Examinez les propositions** dans le fichier Markdown ci-joint
2. **Vérifiez l'exactitude** des comptes, montants, dates
3. **Pour valider**, répondez à cet email avec le tag suivant dans votre message:

   **[_Head] VALIDE:**

4. Vous pouvez modifier le fichier Markdown avant de répondre (optionnel)
5. Joignez le fichier modifié si vous avez apporté des corrections

---

**⏰ _Head attendra votre réponse au prochain réveil automatique.**

Merci,
_Head.Soeurise
"""
            
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            
            # 2. PIÈCE JOINTE: Markdown avec propositions ✅ FIX
            
            try:
                # Créer fichier Markdown temporaire
                md_filename = f"propositions_{type_evt}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                md_filepath = os.path.join(tempfile.gettempdir(), md_filename)
                
                with open(md_filepath, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                
                # Attacher le fichier
                with open(md_filepath, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename= {md_filename}')
                    msg.attach(part)
                
                # Nettoyer le fichier temporaire
                try:
                    os.remove(md_filepath)
                except:
                    pass
            
            except Exception as e:
                print(f"⚠️ Erreur création pièce jointe Markdown: {str(e)[:100]}")
                # Continuer sans pièce jointe si erreur
            
            # 3. ENVOYER L'EMAIL
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.email_from, self.email_password)
                server.send_message(msg)
            
            print(f"✅ Email de propositions envoyé à {email_to} ({type_evt})")
            return True
        
        except Exception as e:
            print(f"❌ Erreur envoi email propositions: {str(e)[:100]}")
            return False
    
    @staticmethod
    def _markdown_to_html(markdown: str) -> str:
        """Conversion simple Markdown → HTML"""
        
        html = markdown
        
        # Headers
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        # Bold/Italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Listes
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.+</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        # Code blocks
        html = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        
        # Paragraphes
        html = re.sub(r'\n\n', r'</p><p>', html)
        html = f"<p>{html}</p>"
        
        # Tables (simple)
        lines = html.split('\n')
        in_table = False
        for i, line in enumerate(lines):
            if '|' in line and not in_table:
                lines[i] = f'<table border="1">{line}'
                in_table = True
            elif '|' in line and in_table:
                lines[i] = f'<tr><td>' + '</td><td>'.join(c.strip() for c in line.split('|')[1:-1]) + '</td></tr>'
            elif in_table and '|' not in line:
                lines[i] = f'</table>\n{line}'
                in_table = False
        
        html = '\n'.join(lines)
        
        return html


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PARSEUR MARKDOWN JSON
# ═══════════════════════════════════════════════════════════════════════════════

class ParseurMarkdownJSON:
    """Parse JSON depuis bloc ```json...``` dans Markdown"""
    
    @staticmethod
    def extraire_json(markdown_text: str) -> Optional[Dict]:
        """
        Extrait le bloc JSON ```json...```
        
        Returns:
            Dict du JSON ou None si introuvable/invalide
        """
        
        # Pattern: ```json...```
        pattern = r'```json\s*\n(.*?)\n```'
        match = re.search(pattern, markdown_text, re.DOTALL)
        
        if not match:
            # Essayer sans backticks
            if '{' in markdown_text and '}' in markdown_text:
                # Chercher {...}
                start = markdown_text.rfind('{')
                end = markdown_text.find('}', start) + 1
                if start >= 0 and end > start:
                    try:
                        return json.loads(markdown_text[start:end])
                    except json.JSONDecodeError:
                        pass
            return None
        
        try:
            json_str = match.group(1)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ Erreur parsing JSON: {str(e)}")
            return None
    
    @staticmethod
    def valider_structure_json(data: Dict, type_evt: str) -> Tuple[bool, str]:
        """
        Valide la structure JSON
        
        Returns:
            (valide, message_erreur)
        """
        
        # Vérifier présence clés obligatoires
        if 'propositions' not in data:
            return False, "Clé 'propositions' manquante"
        
        if 'token' not in data:
            return False, "Clé 'token' manquante"
        
        if not isinstance(data['propositions'], list):
            return False, "'propositions' doit être une liste"
        
        if len(data['propositions']) == 0:
            return False, "Liste 'propositions' vide"
        
        # Valider chaque proposition
        for i, prop in enumerate(data['propositions']):
            if not isinstance(prop, dict):
                return False, f"Proposition {i} n'est pas un dict"
            
            required_keys = ['numero_ecriture', 'type', 'compte_debit', 'compte_credit', 'montant', 'libelle']
            for key in required_keys:
                if key not in prop:
                    return False, f"Proposition {i}: clé '{key}' manquante"
            
            # Valider montant
            try:
                montant = float(prop['montant'])
                if montant <= 0:
                    return False, f"Proposition {i}: montant doit être > 0"
            except (ValueError, TypeError):
                return False, f"Proposition {i}: montant invalide"
        
        return True, ""


if __name__ == "__main__":
    
    print("✅ Module 2 Branches V2 (FIXED) chargé et prêt")
