from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from pages.demarrage import TVAWarningPopup
import os
import sqlite3
from db.database_utils import get_db_path
from datetime import datetime
from utils import resource_path

# Load the KV file for the HomePage layout
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'home.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)

class UnpaidInvoicePopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Factures impayées"
        self.size_hint = (0.8, 0.4)
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        message = Label(
            text="Vous avez des factures impayées.\n Seules les factures payées seront déclarées.",
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

class URSSAF_TVAPopup(Popup):
    def __init__(self, period_info, pending_count, **kwargs):
        super().__init__(**kwargs)
        self.title = "Déclarations URSSAF/TVA en attente"
        self.size_hint = (0.8, 0.4)
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        message = Label(
            text=(f"Vous avez {pending_count} facture(s) en attente de déclaration\n"
                  f"pour la période du {period_info['start'].strftime('%d/%m/%Y')} "
                  f"au {period_info['end'].strftime('%d/%m/%Y')}.\n\n"
                  "Rendez-vous dans la section URSSAF/TVA\n"
                  "pour effectuer vos déclarations."),
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

class HomePage(Screen):
    TVA_IMMEDIATE_SALES_THRESHOLD = 101000  # Set your actual threshold values here
    TVA_IMMEDIATE_SERVICES_THRESHOLD = 39100
    TVA_RETRO_SALES_THRESHOLD = 91900
    TVA_RETRO_SALES_MAX = 101000
    TVA_RETRO_SERVICES_THRESHOLD = 36800
    TVA_RETRO_SERVICES_MAX = 39100

    def on_enter(self):
        # Check for conditions and show relevant popups
        self.check_unpaid_invoices()
        self.check_pending_declarations()
        self.check_tva_status()
        self.update_taux_bnc()

    def update_taux_bnc(self):
        """Update taux_BNC to 0.264 for invoices issued after 01/01/2025."""
        db_path = get_db_path()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Define the date threshold
            date_threshold = "2025-01-01"
            
            # Update taux_BNC for invoices after the date threshold
            cursor.execute("""
                UPDATE Factures 
                SET taux_BNC = 0.264 
                WHERE date_emission > ? AND taux_BNC != 0.264
            """, (date_threshold,))
            
            # Commit changes
            conn.commit()
            print(f"{cursor.rowcount} invoice(s) updated with new taux_BNC.")
            
        except sqlite3.Error as e:
            print(f"Erreur lors de la mise à jour du taux_BNC : {e}")
        finally:
            if conn:
                conn.close()

    def check_unpaid_invoices(self):
        """Check if there are unpaid invoices in the Factures table."""
        db_path = get_db_path()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Factures WHERE status = 0")
            unpaid_count = cursor.fetchone()[0]
            if unpaid_count > 0:
                popup = UnpaidInvoicePopup()
                popup.open()
        except sqlite3.Error as e:
            print(f"Erreur lors de la vérification des factures impayées : {e}")
        finally:
            if conn:
                conn.close()

    def check_pending_declarations(self):
        """Check if there are pending URSSAF or TVA declarations in the Factures table."""
        current_date = datetime.now()
        db_path = get_db_path()
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get declaration frequency
            cursor.execute("SELECT echeance_declaration FROM Info_personnelle ORDER BY id_personnelle DESC LIMIT 1")
            result = cursor.fetchone()
            echeance_declaration = result[0] if result else 3  # Default to quarterly
            
            # Calculate period dates
            current_year = current_date.year
            current_month = current_date.month
            
            if echeance_declaration == 3:  # Quarterly
                quarter = (current_month - 1) // 3
                period_end = datetime(current_year, (quarter * 3) + 3, 1).replace(
                    day=28 if (quarter * 3) + 3 == 2 else 30 if (quarter * 3) + 3 in [4, 6, 9, 11] else 31
                )
                period_start = datetime(current_year, (quarter * 3) + 1, 1)
            else:  # Monthly
                if current_month == 1:
                    period_start = datetime(current_year - 1, 12, 1)
                    period_end = datetime(current_year - 1, 12, 31)
                else:
                    period_start = datetime(current_year, current_month - 1, 1)
                    last_day = 28 if current_month - 1 == 2 else 30 if current_month - 1 in [4, 6, 9, 11] else 31
                    period_end = datetime(current_year, current_month - 1, last_day)
            
            # Only check for pending declarations if the period has ended
            if current_date > period_end:
                cursor.execute("""
                    SELECT COUNT(*) FROM Factures 
                    WHERE date_emission BETWEEN ? AND ?
                    AND status = 1 
                    AND (status_declaration_URSSAF = 0 OR status_declaration_TVA = 0)
                """, (period_start.strftime('%Y-%m-%d'), period_end.strftime('%Y-%m-%d')))
                
                pending_count = cursor.fetchone()[0]
                
                if pending_count > 0:
                    period_info = {
                        'start': period_start,
                        'end': period_end
                    }
                    popup = URSSAF_TVAPopup(period_info=period_info, pending_count=pending_count)
                    popup.open()
                    
        except sqlite3.Error as e:
            print(f"Erreur lors de la vérification des déclarations en attente : {e}")
        finally:
            if conn:
                conn.close()

    def check_tva_status(self):
        """
        Check TVA status and update debut_activite_TVA when status changes.
        Show warning popup if TVA status is triggered without a TVA number.
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

                    # Show warning popup if TVA status is active but no TVA number exists
                    if status_tva == 1 and (ntva is None or ntva.strip() == 'en cours d\'acquisition'):
                        popup = TVAWarningPopup()
                        popup.open()

        except sqlite3.Error as e:
            print(f"Erreur lors de la vérification du statut TVA : {e}")
        finally:
            if conn:
                conn.close()