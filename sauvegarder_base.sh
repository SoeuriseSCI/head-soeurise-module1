#!/bin/bash
#
# SAUVEGARDE BASE DE DONNÉES POSTGRESQL
# ======================================
# Crée un dump complet de la BD PostgreSQL
#

set -e  # Exit on error

echo "================================================================================";
echo "💾 SAUVEGARDE BASE DE DONNÉES POSTGRESQL";
echo "================================================================================";
echo "";

# Vérifier que DATABASE_URL est définie
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERREUR : DATABASE_URL non définie";
    echo "💡 Définissez la variable d'environnement DATABASE_URL";
    exit 1;
fi

# Créer répertoire backups s'il n'existe pas
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

# Nom du fichier de sauvegarde avec timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/soeurise_bd_${TIMESTAMP}.sql"

echo "📁 Répertoire de sauvegarde : $BACKUP_DIR";
echo "📄 Fichier de sauvegarde    : $BACKUP_FILE";
echo "";

# Extraire les informations de connexion depuis DATABASE_URL
# Format: postgresql://user:password@host:port/database
# ou postgres://user:password@host:port/database

# Convertir postgres:// en postgresql:// si nécessaire
DATABASE_URL_FIXED="${DATABASE_URL/postgres:\/\//postgresql:\/\/}"

echo "🔄 Création du dump PostgreSQL...";
echo "";

# Utiliser pg_dump avec DATABASE_URL
if command -v pg_dump &> /dev/null; then
    pg_dump "$DATABASE_URL_FIXED" > "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo "";
        echo "✅ SAUVEGARDE RÉUSSIE !";
        echo "";
        echo "📊 Informations :";
        echo "   Fichier : $BACKUP_FILE";
        echo "   Taille  : $FILE_SIZE";
        echo "";

        # Afficher les statistiques du dump
        echo "📈 Contenu du dump :";
        echo "   Tables créées : $(grep -c 'CREATE TABLE' "$BACKUP_FILE" || echo 0)";
        echo "   Insertions    : $(grep -c 'COPY .* FROM stdin' "$BACKUP_FILE" || echo 0)";
        echo "";

        # Lister les sauvegardes existantes
        echo "📂 Sauvegardes disponibles :";
        ls -lh "$BACKUP_DIR"/*.sql 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
        echo "";

        echo "💡 Pour restaurer :";
        echo "   psql \$DATABASE_URL < $BACKUP_FILE";
        echo "";
    else
        echo "❌ ERREUR lors de la création du dump";
        exit 1;
    fi
else
    echo "❌ ERREUR : pg_dump non trouvé";
    echo "💡 Installez PostgreSQL client : apt-get install postgresql-client";
    exit 1;
fi

echo "================================================================================";
echo "✅ SAUVEGARDE TERMINÉE";
echo "================================================================================";
