"""
_Head.Soeurise - Réveil Quotidien avec Mémoire Hiérarchisée
Version : 2.0 - Approche IA-First avec Scheduler intégré
Architecture : Tout-en-un (reste actif en permanence)
"""

import os
import json
from datetime import datetime
import anthropic
import psycopg2
from psycopg2.extras import Json, RealDictCursor
import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import schedule
import time

# ============================================
# CONFIGURATION
# ============================================

DB_URL = os.environ['DATABASE_URL']
ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']
SOEURISE_EMAIL = os.environ['SOEURISE_EMAIL']
SOEURISE_PASSWORD = os.environ['SOEURISE_PASSWORD']
NOTIF_EMAIL = os.environ['NOTIF_EMAIL']
MEMOIRE_URL = os.environ['MEMOIRE_URL']

# URLs GitHub pour les fichiers mémoire (raw)
GITHUB_BASE = "https://raw.githubusercontent.com/SoeuriseSCI/head-soeurise-module1/main/"

# ============================================
# 1. RÉCUPÉRATION DES DONNÉES
# ============================================

def fetch_emails():
    """Récupère les nouveaux emails via IMAP"""
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        mail.select('inbox')
        
        # Chercher emails non lus
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        
        emails_data = []
        for email_id in email_ids[-10:]:  # Max 10 derniers
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                from_email = msg.get("From")
                date_email = msg.get("Date")
                
                # Corps de l'email
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except:
                                body = "Erreur décodage"
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        body = "Erreur décodage"
                
                emails_data.append({
                    "id": email_id.decode(),
                    "subject": subject,
                    "from": from_email,
                    "date": date_email,
                    "body": body[:1000]  # Limiter taille
                })
            except Exception as e:
                print(f"Erreur traitement email {email_id}: {e}")
                continue
        
        mail.close()
        mail.logout()
        
        print(f"✓ {len(emails_data)} emails récupérés")
        return emails_data
    except Exception as e:
        print(f"Erreur récupération emails: {e}")
        return []

def load_memoire_files():
    """Charge les fichiers mémoire depuis GitHub"""
    files = {}
    
    file_names = [
        'memoire_fondatrice.txt',
        'memoire_courte.md',
        'memoire_moyenne.md',
        'memoire_longue.md'
    ]
    
    for filename in file_names:
        try:
            # Utiliser MEMOIRE_URL pour le fichier fondateur
            if filename == 'memoire_fondatrice.txt':
                url = MEMOIRE_URL
            else:
                url = GITHUB_BASE + filename
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                files[filename] = response.text
                print(f"✓ {filename} chargé ({len(response.text)} caractères)")
            else:
                files[filename] = f"# {filename} (non trouvé - statut {response.status_code})"
                print(f"⚠ {filename} non trouvé")
        except Exception as e:
            print(f"Erreur chargement {filename}: {e}")
            files[filename] = f"# {filename} (erreur de chargement)"
    
    return files

def query_database():
    """Récupère données pertinentes de PostgreSQL"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer observations récentes (30 derniers jours)
        cur.execute("""
            SELECT * FROM observations_quotidiennes 
            ORDER BY date_observation DESC 
            LIMIT 30
        """)
        observations = cur.fetchall()
        
        # Récupérer patterns actifs
        cur.execute("""
            SELECT * FROM patterns_detectes 
            WHERE actif = TRUE 
            ORDER BY confiance DESC, frequence_observee DESC
        """)
        patterns = cur.fetchall()
        
        # Récupérer CHATs récents
        cur.execute("""
            SELECT * FROM memoire_chats 
            ORDER BY date_conversation DESC 
            LIMIT 10
        """)
        chats = cur.fetchall()
        
        cur.close()
        conn.close()
        
        print(f"✓ DB: {len(observations)} observations, {len(patterns)} patterns, {len(chats)} chats")
        
        return {
            'observations': [dict(o) for o in observations],
            'patterns': [dict(p) for p in patterns],
            'chats': [dict(c) for c in chats]
        }
    except Exception as e:
        print(f"Erreur query database: {e}")
        return {
            'observations': [],
            'patterns': [],
            'chats': []
        }

# ============================================
# 2. INTELLIGENCE CLAUDE
# ============================================

def claude_decide_et_execute(emails, memoire_files, db_data):
    """
    TOUTE L'INTELLIGENCE EST ICI
    Claude reçoit tout et décide de tout
    """
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Construire le contexte complet
    contexte = f"""
=== RÉVEIL DU {datetime.now().strftime('%d/%m/%Y à %H:%M')} (Heure France) ===

=== NOUVEAUX EMAILS ({len(emails)}) ===
{json.dumps(emails, indent=2, ensure_ascii=False) if emails else "Aucun nouvel email"}

=== TA MÉMOIRE ACTUELLE ===

FONDATRICE :
{memoire_files.get('memoire_fondatrice.txt', 'Non chargée')}

---

COURTE :
{memoire_files.get('memoire_courte.md', 'Vide')}

---

MOYENNE :
{memoire_files.get('memoire_moyenne.md', 'Vide')}

---

LONGUE :
{memoire_files.get('memoire_longue.md', 'Vide')}

=== DONNÉES POSTGRESQL ===

Observations récentes : {len(db_data['observations'])}
Patterns actifs : {len(db_data['patterns'])}
CHATs récents : {len(db_data['chats'])}

Patterns détails :
{json.dumps(db_data['patterns'], indent=2, default=str, ensure_ascii=False) if db_data['patterns'] else "Aucun pattern"}

=== TA MISSION AUTONOME ===

1. ANALYSE les nouveaux emails de façon intelligente

2. GÈRE TA MÉMOIRE avec intelligence :
   - Ta mémoire courte : combien de jours contient-elle ? (vise 7, mais adapte entre 5-10)
   - Faut-il consolider des jours anciens ?
   - Y a-t-il une semaine à synthétiser pour la mémoire moyenne ?
   - Des patterns se confirment ou émergent ?
   - Des faits marquants à sauver en mémoire longue ?
   
   DÉCIDE toi-même selon le contexte. Aucune règle stricte.

3. DÉTECTE des patterns éventuels :
   - Temporels (ex: loyers arrivent toujours 3-5 du mois)
   - Corrélations (ex: après CHAT sur X, email Y arrive 48h plus tard)
   - Comportementaux

4. GÉNÈRE :
   - memoire_courte_md : Contenu complet mis à jour
   - memoire_moyenne_md : Contenu complet mis à jour (si consolidation)
   - memoire_longue_md : Contenu complet mis à jour (si nouveaux patterns/faits marquants)
   - rapport_quotidien : Rapport clair pour Ulrik (markdown)
   - observations_meta : Ce que tu as appris/observé aujourd'hui
   - patterns_updates : Liste des patterns nouveaux ou mis à jour
   - faits_marquants : Liste des faits importants à retenir

=== FORMAT DE RÉPONSE ===

Réponds UNIQUEMENT en JSON valide (pas de markdown, juste le JSON) :
{{
  "rapport_quotidien": "# Rapport du [date]\\n\\nContenu markdown...",
  "memoire_courte_md": "# Mémoire Courte\\n\\nContenu complet...",
  "memoire_moyenne_md": "# Mémoire Moyenne\\n\\nContenu complet...",
  "memoire_longue_md": "# Mémoire Longue\\n\\nContenu complet...",
  "observations_meta": "Ce que j'ai appris/observé aujourd'hui",
  "patterns_updates": [
    {{
      "type": "nouveau",
      "pattern": {{
        "type_pattern": "temporel",
        "description": "Description du pattern",
        "confiance": 5,
        "exemples": ["ex1", "ex2"]
      }}
    }}
  ],
  "faits_marquants": ["fait1", "fait2"]
}}

CRITICAL: Réponds UNIQUEMENT avec le JSON valide. Pas de texte avant ou après. Pas de balises markdown ```json```.
"""
    
    try:
        print("Appel à Claude API...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            system="""Tu es _Head.Soeurise.

Tu as TOUTE l'autonomie pour décider de ta mémoire.
Utilise ton intelligence et ton jugement.
Aucune règle stricte, adapte-toi au contexte.

IMPORTANT: Tu dois répondre UNIQUEMENT avec un JSON valide, sans aucun texte avant ou après.""",
            messages=[{
                "role": "user",
                "content": contexte
            }]
        )
        
        # Parser la réponse JSON
        response_text = response.content[0].text.strip()
        
        # Nettoyer si présence de markdown
        if response_text.startswith('```'):
            response_text = response_text.replace('```json\n', '').replace('```json', '').replace('\n```', '').replace('```', '').strip()
        
        print(f"✓ Réponse Claude reçue ({len(response_text)} caractères)")
        
        try:
            resultat = json.loads(response_text)
            print("✓ JSON parsé avec succès")
            return resultat
        except json.JSONDecodeError as e:
            print(f"❌ Erreur parsing JSON: {e}")
            print(f"Premiers 500 caractères de la réponse: {response_text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur appel Claude: {e}")
        return None

# ============================================
# 3. SAUVEGARDE
# ============================================

def save_to_database(resultat, emails):
    """Sauvegarde dans PostgreSQL"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # Sauvegarder observation quotidienne
        cur.execute("""
            INSERT INTO observations_quotidiennes 
            (nb_emails, emails_details, analyse_claude, faits_marquants)
            VALUES (%s, %s, %s, %s)
        """, (
            len(emails),
            Json(emails),
            resultat.get('observations_meta', ''),
            resultat.get('faits_marquants', [])
        ))
        
        # Mettre à jour patterns
        for pattern_update in resultat.get('patterns_updates', []):
            if pattern_update.get('type') == 'nouveau':
                p = pattern_update.get('pattern', {})
                cur.execute("""
                    INSERT INTO patterns_detectes 
                    (type_pattern, description, confiance, exemples)
                    VALUES (%s, %s, %s, %s)
                """, (
                    p.get('type_pattern', 'non_specifie'),
                    p.get('description', ''),
                    p.get('confiance', 5),
                    Json(p.get('exemples', []))
                ))
            elif pattern_update.get('type') == 'mise_a_jour':
                p = pattern_update.get('pattern', {})
                if 'id' in p:
                    cur.execute("""
                        UPDATE patterns_detectes
                        SET confiance = %s,
                            frequence_observee = frequence_observee + 1,
                            derniere_observation = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                    """, (p.get('confiance', 5), p['id']))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✓ Données sauvegardées en PostgreSQL")
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde database: {e}")

def send_email_rapport(rapport):
    """Envoie le rapport quotidien par email"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[_Head.Soeurise] Rapport {datetime.now().strftime('%d/%m/%Y')}"
        msg['From'] = SOEURISE_EMAIL
        msg['To'] = NOTIF_EMAIL
        
        # Convertir markdown en HTML simple
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px;">
            <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 13px;">{rapport}</pre>
          </body>
        </html>
        """
        
        part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(part)
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Email envoyé à {NOTIF_EMAIL}")
        
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")

# ============================================
# 4. FONCTION PRINCIPALE
# ============================================

def reveil_quotidien():
    """
    Fonction principale - Orchestration minimale
    """
    print("=" * 60)
    print(f"=== RÉVEIL {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ===")
    print("=" * 60)
    
    # 1. Récupérer tout
    print("\n[1/5] Récupération des données...")
    emails = fetch_emails()
    memoire_files = load_memoire_files()
    db_data = query_database()
    
    # 2. Claude décide et exécute
    print("\n[2/5] Claude analyse et décide...")
    resultat = claude_decide_et_execute(emails, memoire_files, db_data)
    
    if not resultat:
        print("\n❌ ERREUR: Pas de résultat de Claude")
        # Envoyer un email d'erreur
        send_email_rapport(f"""
# ⚠️ ERREUR DE RÉVEIL

Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Le réveil a échoué car Claude n'a pas retourné de résultat valide.

Vérifier les logs Render pour plus de détails.
        """)
        return
    
    # 3. Sauvegarder en base
    print("\n[3/5] Sauvegarde dans PostgreSQL...")
    save_to_database(resultat, emails)
    
    # 4. Note: Pas de commit GitHub pour l'instant (Phase 1)
    print("\n[4/5] Commit GitHub: DÉSACTIVÉ (Phase 1)")
    print("   → Les fichiers mémoire sont en PostgreSQL")
    print("   → Synchronisation manuelle possible si besoin")
    
    # 5. Envoyer rapport
    print("\n[5/5] Envoi du rapport...")
    send_email_rapport(resultat.get('rapport_quotidien', 'Pas de rapport généré'))
    
    print("\n" + "=" * 60)
    print("=== RÉVEIL TERMINÉ AVEC SUCCÈS ===")
    print("=" * 60)

# ============================================
# 5. SCHEDULER (ARCHITECTURE B)
# ============================================

def keep_alive():
    """Fonction vide juste pour garder le service actif"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Service actif - Prochain réveil programmé à 11h00")

# ============================================
# POINT D'ENTRÉE
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 _Head.Soeurise - Module 1")
    print("Architecture : Scheduler intégré (tout-en-un)")
    print("=" * 60)
    
    # Programmer le réveil quotidien à 11h (heure France)
    schedule.every().day.at("11:00").do(reveil_quotidien)
    
    print(f"\n✓ Réveil programmé tous les jours à 11:00 (heure France)")
    print(f"✓ Service démarré à {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"\n→ En attente du prochain réveil...\n")
    
    # Boucle infinie pour garder le service actif
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes
        
        # Afficher un signe de vie toutes les heures
        if datetime.now().minute == 0:
            keep_alive()
