from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None

def upgrade():
    op.execute('''CREATE TABLE exercices_comptables (id SERIAL PRIMARY KEY, annee INT UNIQUE NOT NULL, date_debut DATE NOT NULL, date_fin DATE NOT NULL, statut VARCHAR(50), description TEXT, created_at TIMESTAMP, updated_at TIMESTAMP);
    CREATE TABLE plans_comptes (id SERIAL PRIMARY KEY, numero_compte VARCHAR(10) UNIQUE NOT NULL, libelle VARCHAR(255) NOT NULL, type_compte VARCHAR(50) NOT NULL, classe INT, description TEXT, actif BOOLEAN, created_at TIMESTAMP);
    CREATE TABLE immobilisations (id SERIAL PRIMARY KEY, numero_immobilisation VARCHAR(50) UNIQUE NOT NULL, libelle VARCHAR(255) NOT NULL, compte_immobilisation VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte), compte_amortissement VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte), valeur_brute NUMERIC(12,2) NOT NULL, date_acquisition DATE NOT NULL, methode_amortissement VARCHAR(50) NOT NULL, duree_amortissement INT NOT NULL, created_at TIMESTAMP, updated_at TIMESTAMP);
    CREATE TABLE ecritures_comptables (id SERIAL PRIMARY KEY, exercice_id INT NOT NULL REFERENCES exercices_comptables(id), numero_ecriture VARCHAR(50) NOT NULL, date_ecriture DATE NOT NULL, libelle_ecriture VARCHAR(255) NOT NULL, compte_debit VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte), compte_credit VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte), montant NUMERIC(12,2) NOT NULL, created_at TIMESTAMP);
    CREATE TABLE calculs_amortissements (id SERIAL PRIMARY KEY, immobilisation_id INT NOT NULL REFERENCES immobilisations(id), exercice_id INT NOT NULL REFERENCES exercices_comptables(id), montant_amortissement NUMERIC(12,2) NOT NULL, created_at TIMESTAMP);
    CREATE TABLE evenements_comptables (id SERIAL PRIMARY KEY, email_id VARCHAR(255) UNIQUE, email_from VARCHAR(255) NOT NULL, email_date TIMESTAMP NOT NULL, email_body TEXT NOT NULL, created_at TIMESTAMP);
    CREATE TABLE balances_mensuelles (id SERIAL PRIMARY KEY, exercice_id INT NOT NULL REFERENCES exercices_comptables(id), mois INT NOT NULL, compte_numero VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte), solde_net NUMERIC(12,2), created_at TIMESTAMP);
    CREATE TABLE rapports_comptables (id SERIAL PRIMARY KEY, exercice_id INT NOT NULL REFERENCES exercices_comptables(id), type_rapport VARCHAR(100) NOT NULL, contenu_texte TEXT NOT NULL, created_at TIMESTAMP);''')

def downgrade():
    op.execute('DROP TABLE IF EXISTS rapports_comptables CASCADE; DROP TABLE IF EXISTS balances_mensuelles CASCADE; DROP TABLE IF EXISTS evenements_comptables CASCADE; DROP TABLE IF EXISTS calculs_amortissements CASCADE; DROP TABLE IF EXISTS ecritures_comptables CASCADE; DROP TABLE IF EXISTS immobilisations CASCADE; DROP TABLE IF EXISTS plans_comptes CASCADE; DROP TABLE IF EXISTS exercices_comptables CASCADE;')
