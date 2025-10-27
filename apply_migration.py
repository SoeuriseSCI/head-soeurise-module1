#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour appliquer les migrations Alembic sur la base de données de production

Usage:
    python apply_migration.py         # Applique toutes les migrations en attente
    python apply_migration.py --dry   # Affiche les migrations sans les appliquer
"""
import os
import sys
from alembic import command
from alembic.config import Config

# Charge DATABASE_URL depuis l'environnement ou utilise valeur par défaut
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://soeurise:6cIWYzBxmh8YKBGBH9Or6ohidT6NiCap@dpg-d3ikk7ggjchc73ee4flg-a/soeurise"
)


def main():
    """Applique les migrations Alembic"""

    # Configuration Alembic
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

    # Mode dry-run ?
    dry_run = "--dry" in sys.argv or "--check" in sys.argv

    if dry_run:
        print("🔍 Mode DRY-RUN : Vérification des migrations en attente...")
        print()

        # Affiche l'historique des migrations
        print("📋 Historique des migrations:")
        command.history(alembic_cfg)
        print()

        # Affiche l'état actuel
        print("📍 État actuel:")
        command.current(alembic_cfg)
        print()

        print("💡 Pour appliquer les migrations, exécutez sans --dry")

    else:
        print("🚀 Application des migrations Alembic...")
        print(f"📡 Base de données: {DATABASE_URL[:50]}...")
        print()

        # Affiche l'état avant
        print("📍 État AVANT migration:")
        command.current(alembic_cfg)
        print()

        # Applique les migrations
        try:
            command.upgrade(alembic_cfg, "head")
            print()
            print("✅ Migrations appliquées avec succès!")

            # Affiche l'état après
            print()
            print("📍 État APRÈS migration:")
            command.current(alembic_cfg)

        except Exception as e:
            print(f"❌ Erreur lors de l'application des migrations: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
