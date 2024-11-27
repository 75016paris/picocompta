from kivy.uix.screenmanager import Screen
from utils import resource_path
from kivy.lang import Builder
from kivy.properties import NumericProperty, ListProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.core.window import Window
from db.database_utils import init_database, table_exists, get_db_path
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
import os
import sqlite3
from datetime import datetime, date
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.database_utils import init_database, table_exists, get_db_path


kv_file = resource_path(os.path.join('pages', 'demarrage.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)

class TVAWarningPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Assujettissement TVA"
        self.size_hint = (0.8, 0.4)
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        message = Label(
            text="Renseignez votre N°TVA dans Mes Infos > Modifier",
            halign='center',
            valign='middle',
            text_size=(400, None),
            size_hint_y=0.7
        )
        ok_button = Button(
            text="OK",
            size_hint=(None, None),
            size=(100, 50),
            pos_hint={'center_x': 0.5}
        )
        ok_button.bind(on_release=self.dismiss)
        
        content.add_widget(message)
        content.add_widget(ok_button)
        self.content = content

class DemarragePage(Screen):
    background_color = ListProperty([0.7, 0.7, 0.7, 1])
    progress_mixed_activity = NumericProperty(0)
    # Auto-entrepreneur ceilings
    PLAFOND_BIC_MARCHANDISE = 188700  # Auto-entrepreneur sales ceiling
    PLAFOND_SERVICES = 77700          # Auto-entrepreneur services ceiling

    # TVA thresholds for immediate and retroactive checks
    TVA_IMMEDIATE_SALES_THRESHOLD = 101000
    TVA_IMMEDIATE_SERVICES_THRESHOLD = 39100
    TVA_RETRO_SALES_THRESHOLD = 91900
    TVA_RETRO_SALES_MAX = 101000
    TVA_RETRO_SERVICES_THRESHOLD = 36800
    TVA_RETRO_SERVICES_MAX = 39100

    progress_bic_marchandise = NumericProperty(0)  # Auto-entrepreneur sales progress
    progress_services = NumericProperty(0)         # Auto-entrepreneur services progress
    progress_tva_vente = NumericProperty(0)        # TVA sales progress
    progress_tva_service = NumericProperty(0)      # TVA services progress

    def on_enter(self):
        """Update statistics when entering the page."""
        self.update_statistics()
        self.update_progress_bars()
        Clock.schedule_once(lambda dt: self.update_progress_bars(), 0.1)
        self.check_tva_status()  # Check TVA status and show a popup if needed

    def update_progress_bars(self):
        """Update both auto-entrepreneur and TVA progress bars based on turnover, including caNm and caNs for TVA calculations."""
        db_path = get_db_path()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Retrieve `debut_activite`, `caNm`, and `caNs` from Info_personnelle
            cursor.execute("SELECT debut_activite, caNm, caNs FROM Info_personnelle ORDER BY id_personnelle DESC LIMIT 1")
            info_personnelle = cursor.fetchone()
            
            # Initialize values in case no record is found
            debut_activite_year = None
            caNm = 0
            caNs = 0

            # Check if info_personnelle is not None before unpacking values
            if info_personnelle:
                debut_activite = info_personnelle[0]
                debut_activite_year = datetime.strptime(debut_activite, "%Y-%m-%d").year if debut_activite else None
                caNm = info_personnelle[1] if info_personnelle[1] else 0
                caNs = info_personnelle[2] if info_personnelle[2] else 0

            # Ensure we are in the current year
            current_year = datetime.now().year
            include_caNm_caNs = (debut_activite_year == current_year)

            # Calculate total sales and services for the current year, adding caNm and caNs if applicable
            cursor.execute(f"""
                SELECT 
                    COALESCE(SUM(montant_htBICm), 0) + ? AS total_sales,
                    COALESCE(SUM(montant_htBICs), 0) + COALESCE(SUM(montant_htBNC), 0) + ? AS total_services
                FROM Factures
                WHERE strftime('%Y', date_emission) = ?
            """, (caNm if include_caNm_caNs else 0, caNs if include_caNm_caNs else 0, str(current_year)))

            total_sales, total_services = cursor.fetchone()

            # Update auto-entrepreneur progress bars
            self.progress_bic_marchandise = min(100, (total_sales / self.PLAFOND_BIC_MARCHANDISE) * 100)
            self.progress_services = min(100, (total_services / self.PLAFOND_SERVICES) * 100)

            # Calculate TVA progress bars based on thresholds
            self.progress_tva_vente = min(100, (total_sales / self.TVA_IMMEDIATE_SALES_THRESHOLD) * 100)
            self.progress_tva_service = min(100, (total_services / self.TVA_IMMEDIATE_SERVICES_THRESHOLD) * 100)

            # Mixed activity progress calculation
            mixed_activity_total = total_sales + total_services
            self.progress_mixed_activity = min(100, (mixed_activity_total / self.PLAFOND_BIC_MARCHANDISE) * 100)

            # Set labels if they exist
            if 'label_bic_marchandise' in self.ids:
                self.ids.label_bic_marchandise.text = f"{total_sales:,.2f}€ / {self.PLAFOND_BIC_MARCHANDISE:,}€"
            if 'label_services' in self.ids:
                self.ids.label_services.text = f"{total_services:,.2f}€ / {self.PLAFOND_SERVICES:,}€"
            if 'label_tva_vente' in self.ids:
                self.ids.label_tva_vente.text = f"{total_sales:,.2f}€ / {self.TVA_IMMEDIATE_SALES_THRESHOLD:,}€"
            if 'label_tva_service' in self.ids:
                self.ids.label_tva_service.text = f"{total_services:,.2f}€ / {self.TVA_IMMEDIATE_SERVICES_THRESHOLD:,}€"
            if 'label_mixed_activity' in self.ids:
                self.ids.label_mixed_activity.text = f"{mixed_activity_total:,.2f}€ / {self.PLAFOND_BIC_MARCHANDISE:,}€"

        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des totaux : {e}")
        finally:
            if conn:
                conn.close()

    def check_tva_status(self):
        """
        Check TVA status and update debut_activite_TVA when status changes.
        Show warning popup if TVA status is active but no TVA number exists.
        """
        db_path = get_db_path()
        current_year = datetime.now().year
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get latest status_tva, TVA number, debut_activite, debut_activite_TVA, caNm, and caNs
            cursor.execute("""
                SELECT status_tva, ntva, debut_activite, debut_activite_TVA, caNm, caNs
                FROM Info_personnelle
                ORDER BY id_personnelle DESC
                LIMIT 1
            """)
            result = cursor.fetchone()

            if result:
                status_tva, ntva, debut_activite, debut_activite_tva, caNm, caNs = result
                debut_activite_year = datetime.strptime(debut_activite, "%Y-%m-%d").year if debut_activite else None
                caNm = caNm if caNm else 0
                caNs = caNs if caNs else 0

                # Check if we're in the same year as debut_activite to include caNm and caNs in TVA calculation
                include_caNm_caNs = (debut_activite_year == current_year)

                # Calculate total sales and services for the current year, including caNm and caNs if applicable
                cursor.execute(f"""
                    SELECT 
                        COALESCE(SUM(montant_htBICm), 0) + ? AS total_sales,
                        COALESCE(SUM(montant_htBICs), 0) + COALESCE(SUM(montant_htBNC), 0) + ? AS total_services
                    FROM Factures
                    WHERE strftime('%Y', date_emission) = ?
                """, (caNm if include_caNm_caNs else 0, caNs if include_caNm_caNs else 0, str(current_year)))
                
                total_sales, total_services = cursor.fetchone()

                # Immediate TVA threshold checks
                immediate_sales_tva = total_sales > self.TVA_IMMEDIATE_SALES_THRESHOLD
                immediate_services_tva = total_services > self.TVA_IMMEDIATE_SERVICES_THRESHOLD

                # Retroactive TVA thresholds for past two years (N-1 and N-2)
                turnover = {}
                for offset in (1, 2):
                    year = current_year - offset
                    cursor.execute(f"""
                        SELECT 
                            COALESCE(SUM(montant_htBICm), 0) AS total_sales,
                            COALESCE(SUM(montant_htBICs), 0) + COALESCE(SUM(montant_htBNC), 0) AS total_services
                        FROM Factures
                        WHERE strftime('%Y', date_emission) = '{year}'
                    """)
                    turnover[year] = cursor.fetchone()

                total_sales_n1, total_services_n1 = turnover.get(current_year - 1, (0, 0))
                total_sales_n2, total_services_n2 = turnover.get(current_year - 2, (0, 0))

                # Retroactive TVA conditions
                retroactive_sales_tva = (
                    self.TVA_RETRO_SALES_THRESHOLD < total_sales_n1 <= self.TVA_RETRO_SALES_MAX and
                    self.TVA_RETRO_SALES_THRESHOLD < total_sales_n2 <= self.TVA_RETRO_SALES_MAX
                )
                retroactive_services_tva = (
                    self.TVA_RETRO_SERVICES_THRESHOLD < total_services_n1 <= self.TVA_RETRO_SERVICES_MAX and
                    self.TVA_RETRO_SERVICES_THRESHOLD < total_services_n2 <= self.TVA_RETRO_SERVICES_MAX
                )

                # Trigger TVA status if thresholds are met
                if immediate_sales_tva or immediate_services_tva or retroactive_sales_tva or retroactive_services_tva:
                    # Update TVA status to active
                    cursor.execute("""
                        UPDATE Info_personnelle 
                        SET status_tva = 1 
                        WHERE id_personnelle = (SELECT MAX(id_personnelle) FROM Info_personnelle)
                    """)
                    conn.commit()

                    # Update debut_activite_TVA if not already set
                    if status_tva == 1 and not debut_activite_tva:
                        cursor.execute("""
                            UPDATE Info_personnelle 
                            SET debut_activite_TVA = ? 
                            WHERE id_personnelle = (
                                SELECT id_personnelle 
                                FROM Info_personnelle 
                                ORDER BY id_personnelle DESC LIMIT 1
                            )
                        """, (datetime.now().strftime('%Y-%m-%d'),))
                        conn.commit()

                    # Check if TVA status is active and ntva is missing or empty
                    if status_tva == 1 and (ntva is None or ntva.strip() == 'en cours d\'acquisition'):
                        popup = TVAWarningPopup()
                        popup.open()

        except sqlite3.Error as e:
            print(f"Erreur lors de la vérification du statut TVA : {e}")
        finally:
            if conn:
                conn.close()

    def update_statistics(self):
        """Update client statistics labels."""
        db_path = get_db_path()
        stats = self.get_client_statistics(db_path)
        
        # Check if the ID exists before updating text
        if 'best_client_trimestre' in self.ids:
            self.ids.best_client_trimestre.text = f"Meilleur client (trimestre) : {stats['best_client_quarter']}"
        if 'best_client_historique' in self.ids:
            self.ids.best_client_historique.text = f"Meilleur client (historique) : {stats['best_client_all_time']}"
        if 'worst_payer' in self.ids:
            self.ids.worst_payer.text = f"Client le plus lent : {stats['worst_payer']}"

    def get_client_statistics(self, db_path):
        """Récupère les statistiques clients depuis la base de données."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Obtenir l'année et le trimestre actuels
            current_date = date.today()
            current_year = current_date.year
            current_quarter = (current_date.month - 1) // 3 + 1
            quarter_start = date(current_year, 3 * current_quarter - 2, 1)
            
            # Meilleur client du trimestre (basé sur le total HT)
            cursor.execute("""
                SELECT 
                    c.nom,
                    SUM(f.montant_htBICs + f.montant_htBICm + f.montant_htBNC) as total_ht
                FROM Factures f
                JOIN Clients c ON f.id_client = c.id_client
                WHERE f.date_emission >= ?
                GROUP BY c.id_client
                ORDER BY total_ht DESC
                LIMIT 1
            """, (quarter_start.strftime('%Y-%m-%d'),))
            
            best_quarter = cursor.fetchone()
            best_client_quarter = f"{best_quarter[0]} ({best_quarter[1]:.2f}€)" if best_quarter else "Aucun"

            # Meilleur client historique (basé sur le total HT)
            cursor.execute("""
                SELECT 
                    c.nom,
                    SUM(f.montant_htBICs + f.montant_htBICm + f.montant_htBNC) as total_ht
                FROM Factures f
                JOIN Clients c ON f.id_client = c.id_client
                GROUP BY c.id_client
                ORDER BY total_ht DESC
                LIMIT 1
            """)
            
            best_all_time = cursor.fetchone()
            best_client_all_time = f"{best_all_time[0]} ({best_all_time[1]:.2f}€)" if best_all_time else "Aucun"

            # Client le plus lent à payer (basé sur la différence entre date_status_set et date_emission)
            cursor.execute("""
                SELECT 
                    c.nom,
                    AVG(julianday(f.date_status_set) - julianday(f.date_emission)) as avg_days
                FROM Factures f
                JOIN Clients c ON f.id_client = c.id_client
                WHERE f.status = 1 
                AND f.date_status_set IS NOT NULL
                GROUP BY c.id_client
                ORDER BY avg_days DESC
                LIMIT 1
            """)
            
            worst_payer_result = cursor.fetchone()
            worst_payer = f"{worst_payer_result[0]} ({int(worst_payer_result[1])} jours)" if worst_payer_result else "Aucun"

            return {
                'best_client_quarter': best_client_quarter,
                'best_client_all_time': best_client_all_time,
                'worst_payer': worst_payer
            }

        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des statistiques : {e}")
            return {
                'best_client_quarter': "Erreur",
                'best_client_all_time': "Erreur",
                'worst_payer': "Erreur"
            }
        finally:
            if conn:
                conn.close()

    def continue_to_next_page(self):
        """Gère la navigation vers la page suivante."""
        print("Bouton 'Continuer...' pressé")
        
        db_path = get_db_path()
        if not os.path.exists(db_path):
            print("Database does not exist. Initializing the database.")
            if init_database():
                print("Database initialized successfully.")
            else:
                print("Error during database initialization.")
            self.manager.current = 'inscription'
            return
        
        if not table_exists(db_path, 'Info_Personnelle') or self.is_table_empty(db_path, 'Info_Personnelle'):
            print("Database is empty or missing essential data. Navigating to 'inscription'.")
            self.manager.current = 'inscription'
        else:
            print("Database is populated. Navigating to 'home'.")
            self.manager.current = 'home'

    def is_table_empty(self, db_path, table_name):
        """Vérifie si une table est vide."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            return count == 0
        except sqlite3.Error as e:
            print(f"Error checking if table '{table_name}' is empty: {e}")
            return True
        finally:
            if conn:
                conn.close()