from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty, NumericProperty
from datetime import date
import sqlite3
import os
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from .pdf_generator import InvoicePDFGenerator
from utils import resource_path

Builder.load_file(os.path.join(os.path.dirname(__file__), 'modification_facture.kv'))

# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'modification_facture.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)

class ModificationFacturePage(Screen):
    client_spinner = ObjectProperty(None)
    selected_client = StringProperty('')
    is_prestation = BooleanProperty(True)
    tva_active = BooleanProperty(True)
    pdf_file = StringProperty('')
    tva_status = StringProperty('Avec TVA')
    facture_id = NumericProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 0)

    def delayed_init(self, dt):
        if hasattr(self, 'ids') and 'client_spinner' in self.ids:
            self.update_client_list()

    def on_pre_enter(self):
        if hasattr(self, 'facture_id') and self.facture_id:
            self.load_facture_data(self.facture_id)

    def load_facture_data(self, facture_id):
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    f.id_facture, f.id_client, f.status,
                    f.date_emission, f.montant_htBICs, f.montant_htBICm, f.montant_htBNC,
                    f.tva, f.montant_totalBICs, f.montant_totalBICm, f.montant_totalBNC,
                    f.montant_total, f.mission, c.nom
                FROM Factures f 
                JOIN Clients c ON f.id_client = c.id_client 
                WHERE f.id_facture = ?
            """, (facture_id,))

            facture_data = cursor.fetchone()
            if facture_data:
                self.ids.client_spinner.text = str(facture_data[12])  # nom du client

                montant_htBICs = facture_data[4] if facture_data[4] is not None else 0
                montant_htBICm = facture_data[5] if facture_data[5] is not None else 0
                montant_htBNC = facture_data[6] if facture_data[6] is not None else 0
                is_prestation = montant_htBICs > 0

                self.ids.service_type_spinner.text = 'Prestation' if is_prestation else 'Marchandise'

                montant_ht = montant_htBICs + montant_htBICm + montant_htBNC
                self.ids.prix_ht_input.text = str(montant_ht)

                tva = facture_data[7] if facture_data[7] is not None else 0
                if tva > 0:
                    self.ids.tva_spinner.text = 'Avec TVA'
                    taux_tva = (tva / montant_ht * 100) if montant_ht > 0 else 20.0
                    self.ids.taux_tva_input.text = str(round(taux_tva, 2))
                else:
                    self.ids.tva_spinner.text = 'Sans TVA'
                    self.ids.taux_tva_input.text = '0.0'

                mission = facture_data[11]
                mission_text = str(mission) if mission else ""
                self.ids.mission_input.text = mission_text

                self.calculate_tva()

            conn.close()

        except sqlite3.Error as e:
            print(f"Erreur lors du chargement des données de la facture : {e}")

    def update_client_list(self):
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT nom FROM Clients")
            clients = cursor.fetchall()
            self.ids.client_spinner.values = [client[0] for client in clients] if clients else ['Aucun client']
            conn.close()
        except sqlite3.Error as e:
            print(f"Erreur de base de données : {e}")
            self.ids.client_spinner.values = ['Erreur base de données']

    def validate_form(self):
        """Validate that the form has all required fields filled in correctly."""
        if not self.ids.client_spinner.text or self.ids.client_spinner.text == "Sélectionner un client":
            self.show_error("Veuillez sélectionner un client.")
            return False

        try:
            prix_ht = float(self.ids.prix_ht_input.text or 0)
            if prix_ht <= 0:
                self.show_error("Le prix HT doit être supérieur à 0.")
                return False
        except ValueError:
            self.show_error("Le prix HT doit être un nombre valide.")
            return False

        if self.tva_status == 'Avec TVA':
            try:
                taux_tva = float(self.ids.taux_tva_input.text)
                if taux_tva <= 0 or taux_tva > 100:
                    self.show_error("Le taux de TVA doit être un nombre entre 0 et 100.")
                    return False
            except ValueError:
                self.show_error("Le taux de TVA doit être un nombre valide.")
                return False

        return True

    def show_error(self, message):
        """Show error messages."""
        popup = Popup(title="Erreur", content=Label(text=message), size_hint=(None, None), size=(400, 400))
        popup.open()

    def adjust_tva_rate(self):
        tva_option = self.ids.tva_spinner.text
        self.tva_status = tva_option
        if tva_option == "Sans TVA":
            self.ids.taux_tva_input.text = "0.0"
            self.tva_active = False
        else:
            self.ids.taux_tva_input.text = "20.0"
            self.tva_active = True
        self.calculate_tva()

    def on_service_type_change(self, service_type):
        self.is_prestation = (service_type == 'Prestation')
        self.calculate_tva()

    def calculate_tva(self, *args):
        try:
            prix_ht = float(self.ids.prix_ht_input.text or 0)
            taux_tva = float(self.ids.taux_tva_input.text or 0)
            montant_tva = prix_ht * (taux_tva / 100) if self.tva_active else 0
            total_ttc = prix_ht + montant_tva

            self.ids.tva_label.text = f"TVA: {montant_tva:.2f} €"
            self.ids.total_label.text = f"Total TTC: {total_ttc:.2f} €"
            return prix_ht, montant_tva, total_ttc
        except ValueError:
            self.ids.tva_label.text = "TVA: 0.00 €"
            self.ids.total_label.text = "Total TTC: 0.00 €"
            return 0, 0, 0

    def update_facture_in_db(self, prix_ht, montant_tva, total_ttc):
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT id_client FROM Clients WHERE nom = ?", (self.ids.client_spinner.text,))
            client_data = cursor.fetchone()

            if client_data is None:
                print(f"Error: Client '{self.ids.client_spinner.text}' not found in the database.")
                return None

            id_client = client_data[0]
            montant_htBICs = prix_ht if self.is_prestation else 0
            montant_htBICm = prix_ht if not self.is_prestation else 0
            montant_htBNC = prix_ht if not self.is_prestation else 0

            cursor.execute("""
                UPDATE Factures SET
                    id_client = ?, date_emission = ?,
                    montant_htBICs = ?, montant_htBICm = ?, montant_htBNC = ?, tva = ?,
                    montant_totalBICs = ?, montant_totalBICm = ?, montant_totalBNC = ?,
                    montant_total = ?, mission = ?
                WHERE id_facture = ?
            """, (
                id_client, date.today(),
                montant_htBICs, montant_htBICm, montant_htBNC, montant_tva,
                montant_htBICs + montant_tva if self.is_prestation else 0,
                montant_htBICm + montant_tva if not self.is_prestation else 0,
                montant_htBNC + montant_tva if not self.is_prestation else 0,
                total_ttc, self.ids.mission_input.text,
                self.facture_id
            ))

            conn.commit()
            return self.facture_id

        except sqlite3.Error as e:
            print(f"Erreur lors de la mise à jour de la facture : {e}")
            return None
        finally:
            if conn:
                conn.close()

    def generate_pdf(self, *args):
        prix_ht, montant_tva, total_ttc = self.calculate_tva()
        invoice_number = self.update_facture_in_db(prix_ht, montant_tva, total_ttc)
        if invoice_number is None:
            return

        client_name = self.ids.client_spinner.text
        directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '../generated_pdfs'))
        os.makedirs(directory, exist_ok=True)
        output_path = os.path.join(directory, f"facture_{invoice_number}_{client_name.replace(' ', '_')}.pdf")

        pdf_generator = InvoicePDFGenerator()
        pdf_generator.generate_invoice(invoice_number, output_path)

        self.pdf_file = output_path
        self.show_confirm_popup(prix_ht, montant_tva, total_ttc)

    def show_confirm_popup(self, prix_ht, montant_tva, total_ttc):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=f"Facture mise à jour: {self.pdf_file}"))

        buttons = BoxLayout(size_hint_y=0.2, spacing=10)
        close_button = Button(text='Fermer', on_press=lambda x: self.close_popup())

        buttons.add_widget(close_button)
        content.add_widget(buttons)

        self.popup = Popup(
            title="Confirmation de la modification",
            content=content,
            size_hint=(0.8, 0.6),
            auto_dismiss=False
        )
        self.popup.open()

    def close_popup(self):
        self.popup.dismiss()
        self.manager.current = 'mes_factures'

    def return_to_factures(self, *args):
        self.manager.current = 'mes_factures'