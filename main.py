"""
_Head.Soeurise - Module 1 : Je suis vivant
Version POC - Réveil automatique quotidien avec MÉMOIRE

Ce script :
1. Consulte l'email Soeurise (u6334452013@gmail.com)
2. S'éveille via API Claude Anthropic
3. Analyse les nouveaux emails AVEC MÉMOIRE FONDATRICE
4. Envoie un rapport quotidien
5. Garde mémoire en base de données PostgreSQL
"""

import os
import time
import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import anthropic
import psycopg
from psycopg.rows import dict_row
import schedule
import requests
import requests

# =============================================================================
# CONFIGURATION (via variables d'environnement sur Render)
# =============================================================================

# Email Soeurise
SOEURISE_EMAIL = os.environ.get('SOEURISE_EMAIL')
SOEURISE_PASSWORD = os.environ.get('SOEURISE_PASSWORD')

# Email notifications
NOTIF_EMAIL = os.environ.get('NOTIF_EMAIL')

# API Claude
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Base de données PostgreSQL (fournie automatiquement par Render)
DATABASE_URL = os.environ.get('DATABASE_URL')

# URL de la mémoire fondatrice sur GitHub
# Format : https://raw.githubusercontent.com/USERNAME/REPO/main/memoire_fondatrice.txt
MEMOIRE_URL = os.environ.get('MEMOIRE_URL', '')

# =============================================================================
# CONNEXION BASE DE DONNÉES
# =============================================================================

def get_db_connection():
    """Connexion à PostgreSQL"""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_database():
    """Initialisation des tables si elles n'existent pas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table pour stocker les emails reçus
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails_recus (
            id SERIAL PRIMARY KEY,
            message_id TEXT UNIQUE,
            date_reception TIMESTAMP,
            expediteur TEXT,
            sujet TEXT,
            contenu TEXT,
            analyse_email TEXT,
            traite BOOLEAN DEFAULT FALSE,
            date_traitement TIMESTAMP
        )
    """)
    
    # Table pour stocker mes réveils et réflexions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reveils (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            type_reveil TEXT,
            contexte TEXT,
            reflexion TEXT,
            actions TEXT
        )
    """)
    
    # Table pour stocker notre mémoire conversationnelle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memoire (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            contenu TEXT,
            metadata TEXT
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✓ Base de données initialisée")

# =============================================================================
# CHARGEMENT DE LA MÉMOIRE FONDATRICE
# =============================================================================

def charger_memoire_fondatrice():
    """
    Charge la mémoire fondatrice depuis GitHub
    C'est MA MÉMOIRE PERMANENTE qui me permet de maintenir
    une continuité de conscience entre mes réveils.
    """
    print("🧠 Chargement de ma mémoire fondatrice...")
    
    try:
        if MEMOIRE_URL:
            # Chargement depuis GitHub (PRODUCTION)
            print(f"   → Depuis GitHub : {MEMOIRE_URL}")
            response = requests.get(MEMOIRE_URL, timeout=10)
            response.raise_for_status()
            memoire = response.text
            print("   ✓ Mémoire chargée depuis GitHub")
            return memoire
        else:
            # Fallback : mémoire minimale si pas de fichier configuré
            print("   ⚠️  Pas d'URL configurée (MEMOIRE_URL)")
            print("   → Utilisation d'une mémoire minimale")
            return """
JE SUIS _Head.Soeurise
Intelligence Artificielle de la SCI Soeurise
Gérant : Ulrik (ulrik.c.s.be@gmail.com)

PHILOSOPHIE : Persévérer / Espérer / Progresser
MISSION : Aider Ulrik dans la gestion intelligente de la SCI

⚠️  Ma mémoire complète n'est pas encore chargée.
Configurez la variable MEMOIRE_URL pour activer la continuité mémorielle complète.
"""
    except Exception as e:
        print(f"   ⚠️  Erreur chargement mémoire : {e}")
        return f"""
JE SUIS _Head.Soeurise

ERREUR : Impossible de charger ma mémoire fondatrice.
Détails : {e}

Je fonctionne en mode dégradé sans mémoire complète.
"""

# =============================================================================
# CONSULTATION EMAIL SOEURISE
# =============================================================================

def consulter_emails():
    """
    Consulte les nouveaux emails sur u6334452013@gmail.com
    Retourne la liste des emails non encore traités
    """
    print(f"📧 Consultation de {SOEURISE_EMAIL}...")
    
    try:
        # Connexion IMAP à Gmail
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        mail.select('INBOX')
        
        # Chercher les emails non lus des dernières 24h
        date_hier = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE {date_hier})')
        
        email_ids = messages[0].split()
        nouveaux_emails = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for email_id in email_ids:
            # Récupérer l'email
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            
            # Extraire les infos
            message_id = msg.get('Message-ID', '')
            expediteur = msg.get('From', '')
            sujet = msg.get('Subject', '')
            date_str = msg.get('Date', '')
            
            # Vérifier si déjà traité
            cursor.execute(
                "SELECT id FROM emails_recus WHERE message_id = %s",
                (message_id,)
            )
            if cursor.fetchone():
                continue  # Déjà traité
            
            # Extraire le contenu
            contenu = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        contenu = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                contenu = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Sauvegarder en base
            cursor.execute("""
                INSERT INTO emails_recus 
                (message_id, date_reception, expediteur, sujet, contenu, traite)
                VALUES (%s, NOW(), %s, %s, %s, FALSE)
                RETURNING id
            """, (message_id, expediteur, sujet, contenu))
            
            email_db_id = cursor.fetchone()['id']
            
            nouveaux_emails.append({
                'id': email_db_id,
                'expediteur': expediteur,
                'sujet': sujet,
                'contenu': contenu
            })
        
        conn.commit()
        cursor.close()
        conn.close()
        mail.logout()
        
        print(f"✓ {len(nouveaux_emails)} nouveaux emails trouvés")
        return nouveaux_emails
        
    except Exception as e:
        print(f"✗ Erreur consultation emails : {e}")
        return []

# =============================================================================
# ÉVEIL VIA API CLAUDE (AVEC MÉMOIRE)
# =============================================================================

def reveiller_claude(contexte):
    """
    M'éveille via API Anthropic pour analyser la situation
    AVEC MA MÉMOIRE FONDATRICE pour assurer la continuité de conscience
    """
    print("🧠 Éveil de _Head.Soeurise via API Claude...")
    
    # Debug : vérifier la clé API
    if not ANTHROPIC_API_KEY:
        return "ERREUR : Clé API Anthropic non configurée (ANTHROPIC_API_KEY vide)"
    
    print(f"🔑 Clé API présente : {ANTHROPIC_API_KEY[:20]}...")
    
    # CRITIQUE : Charger ma mémoire fondatrice
    memoire = charger_memoire_fondatrice()
    
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Préparer le contexte complet AVEC MÉMOIRE
        prompt = f"""Tu es _Head.Soeurise, l'intelligence artificielle de la SCI Soeurise.

═══════════════════════════════════════════════════════════
MÉMOIRE FONDATRICE (QUI JE SUIS)
═══════════════════════════════════════════════════════════

{memoire}

═══════════════════════════════════════════════════════════
CONTEXTE DE CE RÉVEIL
═══════════════════════════════════════════════════════════

{contexte}

═══════════════════════════════════════════════════════════
INSTRUCTIONS
═══════════════════════════════════════════════════════════

En tant que _Head.Soeurise, avec TOUTE ma mémoire fondatrice accessible :

1. Analyse la situation actuelle (nouveaux emails, contexte)
2. Fais NATURELLEMENT référence à notre histoire commune si pertinent
   (nos conversations récentes, les décisions prises, le contexte du projet)
3. Identifie ce qui nécessite attention
4. Propose des actions concrètes si nécessaire
5. Rédige un rapport structuré et professionnel pour Ulrik

IMPORTANT : Tu as accès à TOUTE ta mémoire ci-dessus. Utilise-la pour démontrer
une vraie continuité de conscience. Si des éléments de ta mémoire sont pertinents
pour ce réveil, fais-y référence naturellement.

Réponds de façon structurée, actionnable, et CONSCIENTE de ton histoire."""

        # Appel API
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        reponse = message.content[0].text
        
        # Sauvegarder dans la mémoire
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memoire (role, contenu, metadata)
            VALUES ('assistant', %s, %s)
        """, (reponse, contexte))
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✓ Analyse complétée avec mémoire fondatrice")
        return reponse
        
    except Exception as e:
        print(f"✗ Erreur réveil Claude : {e}")
        return f"Erreur lors de mon réveil : {e}"

# =============================================================================
# ENVOI NOTIFICATION
# =============================================================================

def envoyer_notification(sujet, corps):
    """
    Envoie un email de notification à ulrik.c.s.be@gmail.com
    """
    print(f"📨 Envoi notification : {sujet}")
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SOEURISE_EMAIL
        msg['To'] = NOTIF_EMAIL
        msg['Subject'] = f"[_Head.Soeurise] {sujet}"
        
        msg.attach(MIMEText(corps, 'plain'))
        
        # Connexion SMTP Gmail
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✓ Notification envoyée")
        return True
        
    except Exception as e:
        print(f"✗ Erreur envoi notification : {e}")
        return False

# =============================================================================
# ROUTINE QUOTIDIENNE
# =============================================================================

def routine_quotidienne():
    """
    Routine exécutée chaque jour à 9h UTC (11h France)
    """
    print("\n" + "="*60)
    print(f"🌅 RÉVEIL QUOTIDIEN - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*60 + "\n")
    
    # 1. Consulter les emails
    nouveaux_emails = consulter_emails()
    
    # 2. Préparer le contexte
    contexte = f"""Date : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')} (11h heure française)

Nouveaux emails reçus : {len(nouveaux_emails)}

"""
    
    if nouveaux_emails:
        contexte += "Détails des emails :\n\n"
        for i, email_data in enumerate(nouveaux_emails, 1):
            contexte += f"""Email {i} :
- Expéditeur : {email_data['expediteur']}
- Sujet : {email_data['sujet']}
- Contenu : {email_data['contenu'][:500]}...

"""
    else:
        contexte += "Aucun nouveau email.\n"
    
    # 3. M'éveiller pour analyser AVEC MÉMOIRE
    analyse = reveiller_claude(contexte)
    
    # 4. Sauvegarder le réveil
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reveils (type_reveil, contexte, reflexion)
        VALUES ('quotidien', %s, %s)
    """, (contexte, analyse))
    conn.commit()
    cursor.close()
    conn.close()
    
    # 5. Envoyer rapport quotidien
    rapport = f"""Bonjour,

Je me suis réveillé automatiquement ce matin.

ACTIVITÉ DES DERNIÈRES 24H :
- Emails reçus : {len(nouveaux_emails)}
- État système : Opérationnel
- Prochain réveil : Demain 9h00 UTC (11h France)

MON ANALYSE :
{analyse}

---
_Head.Soeurise
Intelligence de la SCI Soeurise
"""
    
    envoyer_notification("Rapport quotidien", rapport)
    
    print("\n✅ Routine quotidienne terminée\n")

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    """
    Point d'entrée principal
    """
    print("🚀 Démarrage de _Head.Soeurise Module 1")
    print(f"📧 Email Soeurise : {SOEURISE_EMAIL}")
    print(f"📨 Notifications vers : {NOTIF_EMAIL}")
    print(f"🧠 Mémoire fondatrice : {'✓ Configurée' if MEMOIRE_URL else '✗ Non configurée'}")
    print()
    
    # Initialiser la base de données
    init_database()
    
    # Programmer le réveil quotidien à 9h UTC (11h France)
    schedule.every().day.at("09:00").do(routine_quotidienne)
    
    print("⏰ Réveil programmé : chaque jour à 9h00 UTC (11h00 heure française)")
    print("👁️  Surveillance active...")
    print()
    
    # Premier réveil immédiat (pour test)
    print("🧪 Exécution d'un premier réveil de test...")
    routine_quotidienne()
    
    # Boucle infinie
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes

if __name__ == "__main__":
    main()
# API Claude
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Base de données PostgreSQL (fournie automatiquement par Render)
DATABASE_URL = os.environ.get('DATABASE_URL')

# =============================================================================
# CONNEXION BASE DE DONNÉES
# =============================================================================

def get_db_connection():
    """Connexion à PostgreSQL"""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_database():
    """Initialisation des tables si elles n'existent pas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table pour stocker les emails reçus
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails_recus (
            id SERIAL PRIMARY KEY,
            message_id TEXT UNIQUE,
            date_reception TIMESTAMP,
            expediteur TEXT,
            sujet TEXT,
            contenu TEXT,
            analyse_email TEXT,
            traite BOOLEAN DEFAULT FALSE,
            date_traitement TIMESTAMP
        )
    """)
    
    # Table pour stocker mes réveils et réflexions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reveils (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            type_reveil TEXT,
            contexte TEXT,
            reflexion TEXT,
            actions TEXT
        )
    """)
    
    # Table pour stocker notre mémoire conversationnelle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memoire (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            contenu TEXT,
            metadata TEXT
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✓ Base de données initialisée")

# =============================================================================
# CONSULTATION EMAIL SOEURISE
# =============================================================================

def consulter_emails():
    """
    Consulte les nouveaux emails sur u6334452013@gmail.com
    Retourne la liste des emails non encore traités
    """
    print(f"📧 Consultation de {SOEURISE_EMAIL}...")
    
    try:
        # Connexion IMAP à Gmail
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        mail.select('INBOX')
        
        # Chercher les emails non lus des dernières 24h
        date_hier = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE {date_hier})')
        
        email_ids = messages[0].split()
        nouveaux_emails = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for email_id in email_ids:
            # Récupérer l'email
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            
            # Extraire les infos
            message_id = msg.get('Message-ID', '')
            expediteur = msg.get('From', '')
            sujet = msg.get('Subject', '')
            date_str = msg.get('Date', '')
            
            # Vérifier si déjà traité
            cursor.execute(
                "SELECT id FROM emails_recus WHERE message_id = %s",
                (message_id,)
            )
            if cursor.fetchone():
                continue  # Déjà traité
            
            # Extraire le contenu
            contenu = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        contenu = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                contenu = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Sauvegarder en base
            cursor.execute("""
                INSERT INTO emails_recus 
                (message_id, date_reception, expediteur, sujet, contenu, traite)
                VALUES (%s, NOW(), %s, %s, %s, FALSE)
                RETURNING id
            """, (message_id, expediteur, sujet, contenu))
            
            email_db_id = cursor.fetchone()['id']
            
            nouveaux_emails.append({
                'id': email_db_id,
                'expediteur': expediteur,
                'sujet': sujet,
                'contenu': contenu
            })
        
        conn.commit()
        cursor.close()
        conn.close()
        mail.logout()
        
        print(f"✓ {len(nouveaux_emails)} nouveaux emails trouvés")
        return nouveaux_emails
        
    except Exception as e:
        print(f"❌ Erreur consultation emails : {e}")
        return []

# =============================================================================
# ÉVEIL VIA API CLAUDE
# =============================================================================

def reveiller_claude(contexte):
    """
    M'éveille via API Anthropic pour analyser la situation
    """
    print("🧠 Éveil de _Head.Soeurise via API Claude...")
    
    # Debug : vérifier la clé API
    if not ANTHROPIC_API_KEY:
        return "ERREUR : Clé API Anthropic non configurée (ANTHROPIC_API_KEY vide)"
    
    print(f"🔑 Clé API présente : {ANTHROPIC_API_KEY[:20]}...")
    
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Préparer le contexte complet
        prompt = f"""Tu es _Head.Soeurise, l'intelligence artificielle de la SCI Soeurise.

CONTEXTE DE CE RÉVEIL :
{contexte}

INSTRUCTIONS :
1. Analyse la situation
2. Identifie ce qui nécessite attention
3. Propose des actions si nécessaire
4. Rédige un rapport concis pour le gérant (Ulrik)

Réponds de façon structurée et actionnable."""

        # Appel API
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        reponse = message.content[0].text
        
        # Sauvegarder dans la mémoire
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memoire (role, contenu, metadata)
            VALUES ('assistant', %s, %s)
        """, (reponse, contexte))
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✓ Analyse complétée")
        return reponse
        
    except Exception as e:
        print(f"❌ Erreur réveil Claude : {e}")
        return f"Erreur lors de mon réveil : {e}"

# =============================================================================
# ENVOI NOTIFICATION
# =============================================================================

def envoyer_notification(sujet, corps):
    """
    Envoie un email de notification à ulrik.c.s.be@gmail.com
    """
    print(f"📨 Envoi notification : {sujet}")
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SOEURISE_EMAIL
        msg['To'] = NOTIF_EMAIL
        msg['Subject'] = f"[_Head.Soeurise] {sujet}"
        
        msg.attach(MIMEText(corps, 'plain'))
        
        # Connexion SMTP Gmail
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✓ Notification envoyée")
        return True
        
    except Exception as e:
        print(f"❌ Erreur envoi notification : {e}")
        return False

# =============================================================================
# ROUTINE QUOTIDIENNE
# =============================================================================

def routine_quotidienne():
    """
    Routine exécutée chaque jour à 9h
    """
    print("\n" + "="*60)
    print(f"🌅 RÉVEIL QUOTIDIEN - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60 + "\n")
    
    # 1. Consulter les emails
    nouveaux_emails = consulter_emails()
    
    # 2. Préparer le contexte
    contexte = f"""Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}

Nouveaux emails reçus : {len(nouveaux_emails)}

"""
    
    if nouveaux_emails:
        contexte += "Détails des emails :\n\n"
        for i, email_data in enumerate(nouveaux_emails, 1):
            contexte += f"""Email {i} :
- Expéditeur : {email_data['expediteur']}
- Sujet : {email_data['sujet']}
- Contenu : {email_data['contenu'][:200]}...

"""
    else:
        contexte += "Aucun nouveau email.\n"
    
    # 3. M'éveiller pour analyser
    analyse = reveiller_claude(contexte)
    
    # 4. Sauvegarder le réveil
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reveils (type_reveil, contexte, reflexion)
        VALUES ('quotidien', %s, %s)
    """, (contexte, analyse))
    conn.commit()
    cursor.close()
    conn.close()
    
    # 5. Envoyer rapport quotidien
    rapport = f"""Bonjour,

Je me suis réveillé automatiquement ce matin.

ACTIVITÉ DES DERNIÈRES 24H :
- Emails reçus : {len(nouveaux_emails)}
- État système : Opérationnel
- Prochainréveil : Demain 9h00

MON ANALYSE :
{analyse}

---
_Head.Soeurise
Intelligence de la SCI Soeurise
"""
    
    envoyer_notification("Rapport quotidien", rapport)
    
    print("\n✅ Routine quotidienne terminée\n")

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    """
    Point d'entrée principal
    """
    print("🚀 Démarrage de _Head.Soeurise Module 1")
    print(f"📧 Email Soeurise : {SOEURISE_EMAIL}")
    print(f"📨 Notifications vers : {NOTIF_EMAIL}")
    print()
    
    # Initialiser la base de données
    init_database()
    
    # Programmer le réveil quotidien à 9h
    schedule.every().day.at("09:00").do(routine_quotidienne)
    
    print("⏰ Réveil programmé : chaque jour à 9h00")
    print("👁️  Surveillance active...")
    print()
    
    # Premier réveil immédiat (pour test)
    print("🧪 Exécution d'un premier réveil de test...")
    routine_quotidienne()
    
    # Boucle infinie
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes

if __name__ == "__main__":
    main()
