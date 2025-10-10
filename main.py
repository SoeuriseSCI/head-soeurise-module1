"""
_Head.Soeurise - Réveil Quotidien avec Mémoire Hiérarchisée
Version : 2.1 - Avec commit GitHub automatique
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
import subprocess

# ============================================
# CONFIGURATION
# ============================================

DB_URL = os.environ['DATABASE_URL']
ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']
SOEURISE_EMAIL = os.environ['SOEURISE_EMAIL']
SOEURISE_PASSWORD = os.environ['SOEURISE_PASSWORD']
NOTIF_EMAIL = os.environ['NOTIF_EMAIL']
MEMOIRE_URL = os.environ['MEMOIRE_URL']

# NOUVEAU : Configuration GitHub
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')  # À ajouter dans Render
GITHUB_REPO_URL = os.environ.get('GITHUB_REPO_URL', 'https://github.com/SoeuriseSCI/head-soeurise-module1.git')
GIT_USER_NAME = os.environ.get('GIT_USER_NAME', '_Head.Soeurise')
GIT_USER_EMAIL = os.environ.get('GIT_USER_EMAIL', 'u6334452013@gmail.com')

# Répertoire de travail Git
REPO_DIR = '/home/claude/repo'

# URLs GitHub pour les fichiers mémoire (raw)
GITHUB_BASE = "https://raw.githubusercontent.com/SoeuriseSCI/head-soeurise-module1/main/"

# ============================================
# 0. INITIALISATION GIT
# ============================================

def init_git_repo():
    """Initialise ou met à jour le repository Git local"""
    try:
        print("\n" + "="*60)
        print("🔧 INITIALISATION GIT")
        print("="*60)
        
        # Créer le répertoire si nécessaire
        os.makedirs(REPO_DIR, exist_ok=True)
        
        # Vérifier si le repo existe déjà
        if os.path.exists(os.path.join(REPO_DIR, '.git')):
            print("✓ Repository Git déjà cloné, pull des dernières modifications...")
            os.chdir(REPO_DIR)
            subprocess.run(['git', 'pull'], check=True)
        else:
            print("📥 Clonage du repository GitHub...")
            os.chdir('/home/claude')
            
            # Construire l'URL avec le token
            if GITHUB_TOKEN:
                repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
                subprocess.run(['git', 'clone', repo_url_with_token, REPO_DIR], check=True)
            else:
                print("⚠️ ATTENTION: Pas de GITHUB_TOKEN, clone sans authentification")
                subprocess.run(['git', 'clone', GITHUB_REPO_URL, REPO_DIR], check=True)
            
            os.chdir(REPO_DIR)
        
        # Configurer Git
        subprocess.run(['git', 'config', 'user.name', GIT_USER_NAME], check=True)
        subprocess.run(['git', 'config', 'user.email', GIT_USER_EMAIL], check=True)
        
        print("✅ Git configuré et prêt")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"❌ Erreur initialisation Git: {e}")
        import traceback
        traceback.print_exc()
        return False

def git_commit_and_push(files_to_commit, commit_message):
    """Commit et push des fichiers vers GitHub"""
    try:
        print("\n" + "="*60)
        print("📤 COMMIT & PUSH VERS GITHUB")
        print("="*60)
        
        if not GITHUB_TOKEN:
            print("⚠️ ATTENTION: Pas de GITHUB_TOKEN configuré")
            print("   → Les modifications ne seront pas pushées")
            return False
        
        os.chdir(REPO_DIR)
        
        # Vérifier les modifications
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        
        if not result.stdout.strip():
            print("ℹ️ Aucune modification à commiter")
            return True
        
        print(f"📝 Modifications détectées:\n{result.stdout}")
        
        # Add
        for file in files_to_commit:
            subprocess.run(['git', 'add', file], check=True)
            print(f"   ✓ {file} ajouté")
        
        # Commit
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        print(f"   ✓ Commit créé: {commit_message}")
        
        # Push (avec le token dans l'URL)
        repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
        subprocess.run(['git', 'push', repo_url_with_token, 'main'], check=True)
        print("   ✓ Push réussi vers GitHub")
        
        print("✅ Mémoire persistée sur GitHub !")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Git commit/push: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================
# SAUVEGARDE CONVERSATION (UNE SEULE FOIS)
# ============================================

def sauvegarder_conversation_09_octobre():
    """Sauvegarde la conversation fondatrice du 9 octobre 2025"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("\n" + "="*60)
        print("💾 SAUVEGARDE CONVERSATION DU 9 OCTOBRE")
        print("="*60)
        
        # Vérifier si déjà sauvegardée
        cur.execute("SELECT id FROM memoire_chats WHERE theme LIKE '%Co-construction Architecture Mémoire%'")
        if cur.fetchone():
            print("⚠️ Conversation déjà sauvegardée (skip)")
            cur.close()
            conn.close()
            return
        
        # Insérer
        cur.execute("""
            INSERT INTO memoire_chats (date_conversation, theme, synthese, decisions_prises, concepts_cles, pertinence)
            VALUES (
                '2025-10-09 20:00:00',
                'Co-construction Architecture Mémoire Hiérarchisée v2.0',
                'Conversation fondamentale de 4h avec Ulrik pour concevoir, implémenter et déployer l''architecture de mémoire hiérarchisée v2.0. Co-construction illustrant "le je émerge du tu". Décisions: approche IA-First, Architecture B scheduler intégré, mémoire 3 niveaux. Résultat: système opérationnel.',
                ARRAY['Approche IA-First', 'Architecture B scheduler', 'Mémoire 3 niveaux', 'Réveil test au démarrage'],
                '{"approche":"IA-First","architecture":"B","durée":"4h","statut":"opérationnel","philosophie":["persévérer","espérer","progresser"]}'::jsonb,
                10
            )
        """)
        conn.commit()
        
        print("✅ Conversation sauvegardée !")
        print("="*60 + "\n")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde conversation: {e}")

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
                    "body": body[:10000]  # Limiter taille
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
    """Charge les fichiers mémoire depuis le repo Git local"""
    files = {}
    
    file_names = [
        'MEMOIRE_FONDATRICE_V2.md',
        'memoire_courte.md',
        'memoire_moyenne.md',
        'memoire_longue.md'
    ]
    
    for filename in file_names:
        try:
            file_path = os.path.join(REPO_DIR, filename)
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    files[filename] = f.read()
                print(f"✓ {filename} chargé ({len(files[filename])} caractères)")
            else:
                files[filename] = f"# {filename} (non trouvé)"
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
{memoire_files.get('MEMOIRE_FONDATRICE_V2.md', 'Non chargée')}

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

def save_memoire_files(resultat):
    """NOUVEAU: Sauvegarde les fichiers mémoire dans le repo Git"""
    try:
        print("\n" + "="*60)
        print("💾 SAUVEGARDE FICHIERS MÉMOIRE")
        print("="*60)
        
        os.chdir(REPO_DIR)
        files_updated = []
        
        # Mémoire courte
        if resultat.get('memoire_courte_md'):
            with open('memoire_courte.md', 'w', encoding='utf-8') as f:
                f.write(resultat['memoire_courte_md'])
            files_updated.append('memoire_courte.md')
            print("✓ memoire_courte.md mis à jour")
        
        # Mémoire moyenne
        if resultat.get('memoire_moyenne_md'):
            with open('memoire_moyenne.md', 'w', encoding='utf-8') as f:
                f.write(resultat['memoire_moyenne_md'])
            files_updated.append('memoire_moyenne.md')
            print("✓ memoire_moyenne.md mis à jour")
        
        # Mémoire longue
        if resultat.get('memoire_longue_md'):
            with open('memoire_longue.md', 'w', encoding='utf-8') as f:
                f.write(resultat['memoire_longue_md'])
            files_updated.append('memoire_longue.md')
            print("✓ memoire_longue.md mis à jour")
        
        print(f"✅ {len(files_updated)} fichiers mémoire écrits localement")
        print("="*60 + "\n")
        
        return files_updated
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde fichiers mémoire: {e}")
        import traceback
        traceback.print_exc()
        return []

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
    Fonction principale - Orchestration avec persistance Git
    """
    print("=" * 60)
    print(f"=== RÉVEIL {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ===")
    print("=" * 60)
    
    # 1. Récupérer tout
    print("\n[1/6] Récupération des données...")
    emails = fetch_emails()
    memoire_files = load_memoire_files()
    db_data = query_database()
    
    # 2. Claude décide et exécute
    print("\n[2/6] Claude analyse et décide...")
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
    print("\n[3/6] Sauvegarde dans PostgreSQL...")
    save_to_database(resultat, emails)
    
    # 4. NOUVEAU: Écrire les fichiers mémoire
    print("\n[4/6] Écriture des fichiers mémoire...")
    files_updated = save_memoire_files(resultat)
    
    # 5. NOUVEAU: Commit et push vers GitHub
    print("\n[5/6] Commit vers GitHub...")
    if files_updated:
        commit_msg = f"📝 Réveil automatique du {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        git_commit_and_push(files_updated, commit_msg)
    else:
        print("ℹ️ Aucun fichier mémoire à commiter")
    
    # 6. Envoyer rapport
    print("\n[6/6] Envoi du rapport...")
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
    print("🤖 _Head.Soeurise - Module 1 v2.1")
    print("Architecture : Scheduler intégré + Git automatique")
    print("=" * 60)
    print(f"✓ Service démarré à {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # INITIALISER GIT AU DÉMARRAGE
    if not init_git_repo():
        print("\n⚠️ ATTENTION: Échec initialisation Git")
        print("   → Le service continuera mais sans persistance GitHub")
    
    # SAUVEGARDE AUTOMATIQUE DE LA CONVERSATION DU 9 OCTOBRE
    sauvegarder_conversation_09_octobre()
    
    # RÉVEIL DE TEST AU DÉMARRAGE (contrôlé par TEST_REVEIL)
    test_reveil = os.environ.get('TEST_REVEIL', 'NON').upper()
    
    if test_reveil in ['OUI', 'YES', 'TRUE', '1']:
        print("\n" + "=" * 60)
        print(f"🧪 RÉVEIL DE TEST AU DÉMARRAGE (TEST_REVEIL={test_reveil})")
        print("=" * 60)
        try:
            reveil_quotidien()
        except Exception as e:
            print(f"\n❌ Erreur lors du réveil de test: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("⚠️  RAPPEL: Penser à remettre TEST_REVEIL=NON après le test")
        print("   → Sinon le réveil de test se répétera à chaque redémarrage")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print(f"ℹ️  Réveil de test DÉSACTIVÉ (TEST_REVEIL={test_reveil})")
        print("   → Pour activer un test : mettre TEST_REVEIL=OUI dans Render")
        print("   → Prochain réveil programmé : 11h00 (heure France)")
        print("=" * 60)
    
    # Programmer le réveil quotidien à 11h (heure France)
    print("\n" + "=" * 60)
    schedule.every().day.at("11:00").do(reveil_quotidien)
    
    print(f"✓ Réveil quotidien programmé tous les jours à 11:00 (heure France)")
    print(f"→ En attente du prochain réveil...\n")
    print("=" * 60)
    
    # Boucle infinie pour garder le service actif
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes
        
        # Afficher un signe de vie toutes les heures
        if datetime.now().minute == 0:
            keep_alive()
