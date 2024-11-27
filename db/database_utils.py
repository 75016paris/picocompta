#db/database_utils.py

import sqlite3
import os

def get_db_path():
    """Retourne le chemin relatif de la base de données."""
    # Utilisation d'un chemin relatif pour la portabilité
    return os.path.join(os.path.dirname(__file__), '..', 'db', 'picocompta.db')

def init_database():
    """Initialise la base de données et crée toutes les tables nécessaires."""
    db_path = get_db_path()  # Utilisation du chemin relatif
    try:
        # Créer le dossier db s'il n'existe pas
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        print(f"Chemin de la base de données : {db_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("Connexion à la base de données réussie.")
        
        # Création des tables (exemple pour Info_Personnelle)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Info_Personnelle (
                id_personnelle INTEGER PRIMARY KEY AUTOINCREMENT,
                nom VARCHAR(50) NOT NULL,
                prenom VARCHAR(50) NOT NULL,
                adresse VARCHAR(100) NOT NULL,
                CP VARCHAR (50) NOT NULL,
                pays VARCHAR(50) NOT NULL,
                email VARCHAR(100) NOT NULL,
                telephone VARCHAR(50) NOT NULL,
                nsiret VARCHAR(50),
                codeape VARCHAR(50),
                nss VARCHAR(50),
                ntva VARCHAR(50),
                rib VARCHAR(50),
                iban VARCHAR(50) NOT NULL,
                bic VARCHAR(50) NOT NULL,
                taux_tva DECIMAL(15, 2) DEFAULT 0.20,
                debut_activite DATE DEFAULT (CURRENT_DATE),
                status_acre BOOLEAN DEFAULT FALSE,
                status_tva BOOLEAN DEFAULT FALSE,
                debut_activite_TVA DATE,
                echeance_declaration INTERGER DEFAULT 3,
                dernier_numero_facture INTEGER DEFAULT 0,
                caNs INTEGER,
                caNm INTEGER,
                activite_principal VARCHAR(50)
            )
        ''')
        print("Table Info_Personnelle vérifiée/créée avec succès.")

        # Création de la table Clients
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Clients (
                id_client INTEGER PRIMARY KEY AUTOINCREMENT,
                nom VARCHAR(50) NOT NULL,
                adresse VARCHAR(100),
                CP VARCHAR(100),
                pays VARCHAR(50),
                email VARCHAR(100),
                nsiret VARCHAR(100),
                ntva VARCHAR(50)
            )
        ''')
        print("Table Clients vérifiée/créée avec succès.")

         # Création de la table Déclaration
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Declarations_Zero (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,  -- 'URSSAF' ou 'TVA'
            date_debut DATE NOT NULL,
            date_fin DATE NOT NULL,
            date_declaration DATETIME DEFAULT CURRENT_TIMESTAMP,
            commentaire TEXT
            )
        ''')
        print("Table Déclaration vérifiée/créée avec succès.")

        # Création de la table Factures
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Factures (
                id_facture INTEGER PRIMARY KEY AUTOINCREMENT,
                id_client INTEGER,
                status INTEGER DEFAULT 0,
                status_declaration_URSSAF INTEGER DEFAULT 0,
                status_declaration_TVA INTEGER DEFAULT 0,
                date_status_set DATE,
                date_emission DATE,
                date_echeance DATE,
                montant_htBICs DECIMAL(15, 2) DEFAULT 0,
                montant_htBICm DECIMAL(15, 2) DEFAULT 0,
                montant_htBNC DECIMAL(15, 2) DEFAULT 0,
                montant_ht DECIMAL(15, 2) GENERATED ALWAYS AS (COALESCE(montant_htBICs, 0) + COALESCE(montant_htBICm, 0) + COALESCE(montant_htBNC, 0)) STORED,
                tva DECIMAL(5, 2) DEFAULT 0,
                montant_totalBICs DECIMAL(15, 2) DEFAULT 0,
                montant_totalBICm DECIMAL(15, 2) DEFAULT 0,
                montant_totalBNC DECIMAL(15, 2) DEFAULT 0,
                montant_total DECIMAL(15, 2) DEFAULT 0,
                mission TEXT DEFAULT '',
                urssaf_status INTEGER DEFAULT 0,
                tva_status INTEGER DEFAULT 0,
                taux_tva DECIMAL(15, 2) DEFAULT 0,
                type_activite VARCHAR(50),
                taux_BICs DECIMAL(15, 2) DEFAULT 0.215,
                taux_BICm DECIMAL(15, 2) DEFAULT 0.124,
                taux_BNC DECIMAL(15, 2) DEFAULT 0.248,
                numero_facture INTEGER,
                FOREIGN KEY (id_client) REFERENCES Clients(id_client)
            );
        ''')
        print("Table Factures vérifiée/créée avec succès.")

    
        print("Toutes les tables ont été vérifiées/créées avec succès.")
        return True

    except sqlite3.Error as e:
        print(f"Erreur lors de l'initialisation de la base de données : {e}")
        return False

    finally:
        if conn:
            conn.close()

def table_exists(db_path, table_name):
    """Vérifie si une table existe dans la base de données."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT name 
            FROM sqlite_master 
            WHERE type='table' AND name='{table_name}'
        """)

        return cursor.fetchone() is not None

    except sqlite3.Error as e:
        print(f"Erreur lors de la vérification de la table : {e}")
        return False

    finally:
        if conn:
            conn.close()

def get_all_tables(db_path=None):
    """Retourne la liste de toutes les tables dans la base de données."""
    db_path = db_path if db_path else get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name 
            FROM sqlite_master 
            WHERE type='table'
            ORDER BY name;
        """)

        tables = cursor.fetchall()
        return [table[0] for table in tables]

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération des tables : {e}")
        return []

    finally:
        if conn:
            conn.close()