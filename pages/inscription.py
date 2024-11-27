# inscription.py
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
import os
import sqlite3
from kivy.clock import Clock
from db.database_utils import init_database, table_exists
import datetime
from utils import resource_path

class InscriptionPage(Screen):
    def on_pre_enter(self):
        """Prepare the database and set default values."""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')

        # Initialize the database if it does not exist
        if not os.path.exists(db_path):
            print("Database not found, creating...")
            init_database(db_path)

        # Set default values immediately
        self.set_default_values()

    def set_default_values(self):
        """Set default values for all fields."""
        # Default values for text inputs
        default_hints = {
            'nom': 'Nom',
            'prenom': 'Prénom',
            'adresse': 'Adresse',
            'CP': 'Code Postal',
            'pays': 'Pays',
            'email': 'Email',
            'telephone': 'Téléphone',
            'nsiret': 'Numéro SIRET',
            'codeape': 'Code APE',
            'nss': 'NSS',
            'ntva': 'Numéro TVA',
            'rib': 'RIB',
            'iban': 'IBAN',
            'bic': 'BIC',
            'dernier_numero_facture': '0'
        }

        # Set default hint texts
        for field, hint in default_hints.items():
            if hasattr(self.ids, field):
                self.ids[field].hint_text = hint
                self.ids[field].text = ''

        # Set default spinner values
        if hasattr(self.ids, 'echeance_declaration_spinner'):
            self.ids.echeance_declaration_spinner.text = "Sélectionner"
        if hasattr(self.ids, 'activite_principal_spinner'):
            self.ids.activite_principal_spinner.text = "Sélectionner"

    def get_text_or_hint(self, widget):
        """Return text if entered, otherwise None for required fields."""
        return widget.text.strip() if widget.text.strip() else None

    def save_info(self):
        """Save user input information into the database after validation."""
        info_data = {
            'nom': self.get_text_or_hint(self.ids.nom),
            'prenom': self.get_text_or_hint(self.ids.prenom),
            'adresse': self.get_text_or_hint(self.ids.adresse),
            'CP': self.get_text_or_hint(self.ids.CP),
            'pays': self.get_text_or_hint(self.ids.pays),
            'email': self.get_text_or_hint(self.ids.email),
            'telephone': self.get_text_or_hint(self.ids.telephone),
            'nsiret': self.get_text_or_hint(self.ids.nsiret),
            'codeape': self.get_text_or_hint(self.ids.codeape),
            'nss': self.get_text_or_hint(self.ids.nss),
            'ntva': self.get_text_or_hint(self.ids.ntva), 
            'rib': self.get_text_or_hint(self.ids.rib),
            'iban': self.get_text_or_hint(self.ids.iban),
            'bic': self.get_text_or_hint(self.ids.bic),
            'debut_activite': datetime.datetime.now().strftime('%Y-%m-%d'),
            'activite_principal': self.ids.activite_principal_spinner.text if self.ids.activite_principal_spinner.text != "Sélectionner" else None,
            'echeance_declaration': 1 if self.ids.echeance_declaration_spinner.text == "1 mois" else 3 if self.ids.echeance_declaration_spinner.text == "3 mois" else None,
            'dernier_numero_facture': self.ids.dernier_numero_facture.text.strip() or 0,
            'caNm': self.get_text_or_hint(self.ids.caNm) or 0,  # Input 1 for BIC marchandise
            'caNs': self.get_text_or_hint(self.ids.caNs) or 0,  # Input 2 for BNC
        }

        # Required fields
        required_fields = ['nom', 'prenom', 'adresse', 'CP', 'nsiret', 'codeape', 'iban', 'bic', 'activite_principal', 'echeance_declaration']
        missing_fields = [field for field in required_fields if not info_data[field]]

        if missing_fields:
            self.show_message(f"Required fields are missing:\n{', '.join(missing_fields)}")
            return

        # Insert data into the database
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO Info_Personnelle (
                    nom, prenom, adresse, CP, pays, email, telephone, nsiret,
                    codeape, nss, ntva, rib, iban, bic, debut_activite, activite_principal, echeance_declaration, dernier_numero_facture, 'caNm', 'caNs'
                ) VALUES (
                    :nom, :prenom, :adresse, :CP, :pays, :email, :telephone, :nsiret,
                    :codeape, :nss, :ntva, :rib, :iban, :bic, :debut_activite, :activite_principal, :echeance_declaration, :dernier_numero_facture, :caNm, :caNs
                )
            ''', info_data)
            conn.commit()
            conn.close()

            self.show_message("Personal information saved successfully.", callback=lambda: setattr(self.manager, 'current', 'home'))
        except sqlite3.Error as e:
            self.show_message(f"Error saving data: {e}")

    def show_message(self, message, callback=None):
        """Display a popup message to the user with a 'Next' button."""
        popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        message_label = Label(text=message, size_hint_y=None, height=100)
        suivant_button = Button(text="Next", size_hint_y=None, height=40)

        suivant_button.bind(on_release=lambda instance: popup.dismiss())
        if callback:
            suivant_button.bind(on_release=lambda instance: callback())

        popup_content.add_widget(message_label)
        popup_content.add_widget(suivant_button)

        popup = Popup(title="Message", content=popup_content, size_hint=(0.8, 0.4), auto_dismiss=False)
        popup.open()

# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'inscription.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)