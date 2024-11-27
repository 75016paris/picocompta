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
from datetime import datetime
from utils import resource_path

Builder.load_file(os.path.join(os.path.dirname(__file__), 'nouvelle_facture.kv'))

# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'nouvelle_facture.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)

class NouvelleFacturePage(Screen):
    client_spinner = ObjectProperty(None)
    selected_client = StringProperty('')
    is_prestation = BooleanProperty(True)
    tva_active = BooleanProperty(True)
    pdf_file = StringProperty('')
    tva_status = NumericProperty(0)
    service_type = StringProperty("Sélectionner un type d'activité")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.delayed_init, 0)

    def on_pre_enter(self):
        """Refresh the client list each time the page is opened."""
        self.reset_fields()
        self.load_initial_settings()
        self.update_client_list()

    def reset_fields(self):
        """Reset all editable fields to their default values."""
        # Reset client selection
        self.ids.client_spinner.text = 'Sélectionner un client'
        
        # Reset input fields
        self.ids.mission_input.text = ''
        self.ids.prix_ht_input.text = ''
        
        # Reset calculated values
        self.ids.tva_label.text = 'TVA: 0.00 €'
        self.ids.total_label.text = 'Total TTC: 0.00 €'
        
        # Reset pdf file path
        self.pdf_file = ''

    def delayed_init(self, dt):
        self.update_client_list()
        self.load_initial_settings()

    def load_initial_settings(self):
        """Charge uniquement le type d'activité et les paramètres TVA."""
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT activite_principal, status_tva, dernier_numero_facture, ntva 
                FROM Info_Personnelle 
                WHERE id_personnelle = (SELECT MAX(id_personnelle) FROM Info_Personnelle)
            """)
            result = cursor.fetchone()

            if result:
                activite_principal, status_tva, dernier_numero_facture, ntva = result
                print(f"Valeurs récupérées de la DB : {result}")  # Debug
                
                # Gestion du numéro TVA
                if ntva is None or ntva == "Numéro TVA":
                    cursor.execute("""
                        UPDATE Info_Personnelle 
                        SET ntva = ?
                        WHERE id_personnelle = (SELECT MAX(id_personnelle) FROM Info_Personnelle)
                    """, ("en cours d'acquisition",))
                    conn.commit()
                    self.company_vat = "en cours d'acquisition"
                else:
                    self.company_vat = ntva

                # Configuration du type d'activité
                valid_activities = ['BIC marchandise', 'BIC service', 'BNC']
                self.ids.service_type_spinner.values = valid_activities
                
                # Définir la valeur par défaut depuis activite_principal
                if activite_principal:
                    print(f"Activité principale trouvée : {activite_principal}")  # Debug
                    if activite_principal in valid_activities:
                        def set_spinner_value(dt):
                            self.service_type = activite_principal
                            self.ids.service_type_spinner.text = activite_principal
                            self.is_prestation = (activite_principal == 'BIC service')
                            print(f"Spinner mis à jour avec : {self.ids.service_type_spinner.text}")  # Debug
                        
                        Clock.schedule_once(set_spinner_value, 0)
                    else:
                        print(f"Activité invalide : {activite_principal}")  # Debug

                # Configuration de la TVA
                self.tva_status = status_tva
                if status_tva == 1:
                    self.ids.tva_spinner.text = 'Avec TVA'
                    self.tva_active = True
                    self.ids.taux_tva_input.text = '20.0'
                    self.ids.taux_tva_input.disabled = False
                else:
                    self.ids.tva_spinner.text = 'Sans TVA'
                    self.tva_active = False
                    self.ids.taux_tva_input.text = '0.0'
                    self.ids.taux_tva_input.disabled = True

                self.dernier_numero_facture = dernier_numero_facture

            conn.close()

        except sqlite3.Error as e:
            print(f"Erreur lors du chargement des paramètres initiaux : {e}")
            self.ids.service_type_spinner.values = ['BIC marchandise', 'BIC service', 'BNC']
            self.ids.service_type_spinner.text = 'BIC service'
            self.ids.tva_spinner.text = 'Sans TVA'
            self.tva_status = 0
            self.tva_active = False
            self.is_prestation = True
            self.dernier_numero_facture = '0'
            self.company_vat = "en cours d'acquisition"

    def update_client_list(self):
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT nom FROM Clients ORDER BY nom")
            clients = cursor.fetchall()

            client_list = [client[0] for client in clients] if clients else ['Aucun client']
            self.ids.client_spinner.values = ['Sélectionner un client'] + client_list

            conn.close()

        except sqlite3.Error as e:
            print(f"Erreur de base de données lors de la mise à jour de la liste des clients : {e}")
            self.ids.client_spinner.values = ['Erreur base de données']

    def on_service_type_change(self, service_type):
        """Handles the change of the service type."""
        if service_type == 'BIC service':
            self.is_prestation = True
        else:
            self.is_prestation = False
        self.calculate_tva()

    def adjust_tva_rate(self):
        """Adjust the VAT rate based on the selected option in the dropdown."""
        tva_option = self.ids.tva_spinner.text

        if tva_option == "Sans TVA":
            self.ids.taux_tva_input.text = "0.0"
            self.tva_active = False
            self.tva_status = 0
            self.ids.taux_tva_input.disabled = True
        else:
            self.ids.taux_tva_input.text = "20.0"
            self.tva_active = True
            self.tva_status = 1
            self.ids.taux_tva_input.disabled = False

        self.calculate_tva()

    def validate_form(self):
        """Validate that the form has all required fields filled in correctly."""
        if not self.ids.client_spinner.text or self.ids.client_spinner.text == "Sélectionner un client":
            self.show_error("Veuillez sélectionner un client.")
            return False

        if not self.ids.service_type_spinner.text or self.ids.service_type_spinner.text == "Sélectionner un type d'activité":
            self.show_error("Veuillez sélectionner un type d'activité.")
            return False

        try:
            prix_ht = float(self.ids.prix_ht_input.text or 0)
            if prix_ht <= 0:
                self.show_error("Le prix HT doit être supérieur à 0.")
                return False
        except ValueError:
            self.show_error("Le prix HT doit être un nombre valide.")
            return False

        if self.tva_active:
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
        """Show error messages with OK button."""
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        message_label = Label(
            text=message,
            halign='center',
            valign='middle'
        )
        ok_button = Button(
            text="OK",
            size_hint=(None, None),
            size=(100, 40),
            pos_hint={'center_x': 0.5}
        )
        
        # Création du popup avant de lier le bouton
        popup = Popup(
            title="Erreur",
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        
        # Liaison du bouton à la fermeture du popup
        ok_button.bind(on_release=popup.dismiss)
        
        content.add_widget(message_label)
        content.add_widget(ok_button)
        popup.open()

    def calculate_tva(self, *args):
        """Calculate TVA and update the display."""
        try:
            prix_ht = float(self.ids.prix_ht_input.text or 0)
            taux_tva = float(self.ids.taux_tva_input.text or 0)

            if self.tva_status == 1:
                montant_tva = prix_ht * (taux_tva / 100)
            else:
                montant_tva = 0
                taux_tva = 0

            total_ttc = prix_ht + montant_tva

            # Mise à jour des labels avec les nouveaux montants
            self.ids.tva_label.text = f"TVA ({taux_tva}%): {montant_tva:.2f} €"
            self.ids.total_label.text = f"Total TTC: {total_ttc:.2f} €"
            
            return prix_ht, montant_tva, total_ttc

        except ValueError:
            self.ids.tva_label.text = "TVA (0%): 0.00 €"
            self.ids.total_label.text = "Total TTC: 0.00 €"
            return 0, 0, 0
        
    def generate_pdf(self, *args):
        """Generate the PDF only if the form and VAT numbers are valid."""
        if not self.validate_form():
            return
            
        # Vérification du numéro TVA du client avant de continuer
        if not self.check_client_vat_number():
            return

        prix_ht, montant_tva, total_ttc = self.calculate_tva()
        invoice_number = self.save_facture_to_db(prix_ht, montant_tva, total_ttc)
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

    def check_client_vat_number(self):
        """Check if the selected client has a VAT number when TVA is active."""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        client_name = self.ids.client_spinner.text
        
        # Vérifier seulement si la TVA est active
        if self.tva_status == 1:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT ntva FROM Clients WHERE nom = ?", (client_name,))
                result = cursor.fetchone()
                conn.close()

                if result is None or result[0] is None or result[0].strip() == '':
                    self.show_error("Pas de Numéro de TVA pour le Client, veuillez le renseigner dans Mes Clients > Modifier")
                    return False
                return True
                
            except sqlite3.Error as e:
                print(f"Database error while checking VAT number: {e}")
                return False
        return True
            
#        except sqlite3.Error as e:
#            print(f"Database error while checking VAT number: {e}")
#            return False

    def show_vat_error_popup(self):
        """Display an error popup if the client's VAT number is missing."""
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        message = Label(
            text="Pas de N°TVA pour ce client.\nVeuillez le renseigner dans Mes Clients > Modifier.",
            halign='center',
            valign='middle'
        )
        ok_button = Button(
            text="OK",
            size_hint=(None, None),
            size=(100, 40),
            pos_hint={'center_x': 0.5}
        )
        ok_button.bind(on_release=lambda x: popup.dismiss())
        
        content.add_widget(message)
        content.add_widget(ok_button)
        
        popup = Popup(
            title="Erreur N°TVA",
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        popup.open()

    def show_confirm_popup(self, prix_ht, montant_tva, total_ttc):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=f"Facture générée: {self.pdf_file}"))

        buttons = BoxLayout(size_hint_y=0.2, spacing=10)
        save_button = Button(text='Sauvegarder', on_press=lambda x: self.save_facture())
        cancel_button = Button(text='Annuler', on_press=lambda x: self.cancel_facture())

        buttons.add_widget(save_button)
        buttons.add_widget(cancel_button)
        content.add_widget(buttons)

        self.popup = Popup(
            title="Confirmation de la facture",
            content=content,
            size_hint=(0.8, 0.6),
            auto_dismiss=False
        )
        self.popup.open()

    def save_facture(self):
        self.popup.dismiss()
        self.manager.current = 'home'

    def cancel_facture(self):
        if os.path.exists(self.pdf_file):
            os.remove(self.pdf_file)
        self.popup.dismiss()

    def save_facture_to_db(self, prix_ht, montant_tva, total_ttc):
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            client_name = self.ids.client_spinner.text
            cursor.execute("SELECT id_client FROM Clients WHERE nom = ?", (client_name,))
            client_data = cursor.fetchone()

            if client_data is None:
                print(f"Error: Client '{client_name}' not found in the database.")
                self.show_error("Client non trouvé")
                return None

            id_client = client_data[0]

            # Retrieve the latest invoice number from Info_Personnelle
            cursor.execute("SELECT dernier_numero_facture FROM Info_Personnelle ORDER BY id_personnelle DESC LIMIT 1")
            dernier_numero_facture = cursor.fetchone()[0]
            numero_facture = dernier_numero_facture + 1  # Increment the invoice number

            # Determine montant_htBICs, montant_htBICm, montant_htBNC based on service type
            service_type = self.ids.service_type_spinner.text

            if service_type == 'BIC service':  # Prestation
                montant_htBICs = prix_ht
                montant_htBICs = prix_ht
                montant_htBICm = 0
                montant_htBNC = 0
            elif service_type == 'BIC marchandise':  # Marchandise
                montant_htBICs = 0
                montant_htBICm = prix_ht
                montant_htBNC = 0
            elif service_type == 'BNC':  # BNC
                montant_htBICs = 0
                montant_htBICm = 0
                montant_htBNC = prix_ht
            else:
                # Default case to handle unexpected inputs
                montant_htBICs = 0
                montant_htBICm = 0
                montant_htBNC = 0

            # Insert the new invoice into the Factures table
            cursor.execute("""
                INSERT INTO Factures (
                    id_client, status, date_emission, 
                    montant_htBICs, montant_htBICm, montant_htBNC, tva,
                    montant_totalBICs, montant_totalBICm, montant_totalBNC,
                    montant_total, mission, taux_tva, type_activite,
                    tva_status, numero_facture
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                id_client, 0, date.today(),
                montant_htBICs, montant_htBICm, montant_htBNC, montant_tva,
                montant_htBICs + montant_tva if self.is_prestation else 0,
                montant_htBICm + montant_tva if not self.is_prestation else 0,
                montant_htBNC + montant_tva if not self.is_prestation else 0,
                total_ttc, self.ids.mission_input.text,
                float(self.ids.taux_tva_input.text),  # Store taux_tva as a float
                service_type,
                self.tva_status,  # Store tva_status as 1 or 0
                numero_facture
            ))

            # Update dernier_numero_facture in Info_Personnelle
            cursor.execute("""
                UPDATE Info_Personnelle 
                SET dernier_numero_facture = ? 
                WHERE id_personnelle = (SELECT MAX(id_personnelle) FROM Info_Personnelle)
            """, (numero_facture,))
            conn.commit()

            invoice_number = cursor.lastrowid
            return invoice_number

        except sqlite3.Error as e:
            print(f"Erreur lors de la sauvegarde de la facture : {e}")
            return None
        finally:
            if conn:
                conn.close()

    def return_home(self, *args):
        """Gère la navigation vers la page d'accueil."""
        self.manager.current = 'home'