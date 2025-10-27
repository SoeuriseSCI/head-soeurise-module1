#!/usr/bin/env python3
"""
Utilitaires pour accéder à la base de données PostgreSQL
Charge automatiquement DATABASE_URL depuis .env
"""

import os
import sys
from pathlib import Path

# Charger .env si disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Si dotenv n'est pas installé, essayer de lire .env manuellement
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Importer psycopg2
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 n'est pas installé. Installez-le avec: pip install psycopg2-binary")
    sys.exit(1)


def get_connection():
    """Obtient une connexion à la base de données"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL non définie dans l'environnement ou .env")
    return psycopg2.connect(database_url)


def query(sql, params=None, fetchone=False):
    """
    Exécute une requête SQL et retourne les résultats

    Args:
        sql: Requête SQL
        params: Paramètres de la requête (tuple ou dict)
        fetchone: Si True, retourne une seule ligne au lieu de toutes

    Returns:
        Liste de dictionnaires (ou un seul dict si fetchone=True)
    """
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)
        if fetchone:
            return dict(cur.fetchone()) if cur.rowcount > 0 else None
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def execute(sql, params=None):
    """
    Exécute une requête SQL d'insertion/update/delete

    Args:
        sql: Requête SQL
        params: Paramètres de la requête (tuple ou dict)

    Returns:
        Nombre de lignes affectées
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rowcount = cur.rowcount
        conn.commit()
        return rowcount
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def test_connection():
    """Test la connexion à la base de données"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"✅ Connexion réussie !")
        print(f"PostgreSQL version: {version}")

        # Tester les tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"\n📊 Tables disponibles ({len(tables)}):")
        for table in tables:
            print(f"  - {table}")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False


if __name__ == '__main__':
    # Test si exécuté directement
    test_connection()
