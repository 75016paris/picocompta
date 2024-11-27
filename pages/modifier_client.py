from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
import os
from utils import resource_path
import sqlite3

class ModifierClientPage(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client_id = None

    def on_pre_enter(self):
        """Charge les données du client quand on entre dans la page"""
        if self.client_id:  # Si ID client existe, c'est une modification
            self.charger_client(self.client_id)
            self.ids.page_title.text = "Modifier Client"
            self.ids.save_button.text = "Mettre à jour"

    def charger_client(self, client_id):
        """Charge les données du client depuis la base de données"""
        self.client_id = client_id  # Stocke l'ID du client
        
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nom, adresse, CP, pays, email, ntva, nsiret
                FROM Clients 
                WHERE id_client = ?
            """, (client_id,))
            
            client_data = cursor.fetchone()
            if client_data:
                self.ids.nom.text = client_data[0] or ""
                self.ids.adresse.text = client_data[1] or ""
                self.ids.cp.text = client_data[2] or ""
                self.ids.pays.text = client_data[3] or ""
                self.ids.email.text = client_data[4] or ""
                self.ids.ntva.text = client_data[5] or ""
                self.ids.nsiret.text = client_data[6] or ""

            conn.close()

        except sqlite3.Error as e:
            print(f"Erreur lors du chargement des données du client : {e}")
            self.show_message(f"Erreur lors du chargement des données : {e}")

    def show_message(self, message, callback=None):
        """Display a popup message to the user with a 'Suivant' button."""
        popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        message_label = Label(
            text=message,
            size_hint_y=None,
            height=100,
            text_size=(400, None),
            halign='center',
            valign='middle'
        )
        suivant_button = Button(text="Suivant", size_hint_y=None, height=40)

        suivant_button.bind(on_release=lambda instance: popup.dismiss())
        if callback:
            suivant_button.bind(on_release=lambda instance: callback())

        popup_content.add_widget(message_label)
        popup_content.add_widget(suivant_button)

        popup = Popup(title="Message", content=popup_content, size_hint=(0.8, 0.4), auto_dismiss=False)
        popup.open()

    def save_client(self):
        # Récupérer les valeurs des champs
        client_data = {
            'nom': self.ids.nom.text.strip(),
            'adresse': self.ids.adresse.text.strip(),
            'cp': self.ids.cp.text.strip(),
            'pays': self.ids.pays.text.strip(),
            'email': self.ids.email.text.strip(),
            'ntva': self.ids.ntva.text.strip(),
            'nsiret': self.ids.nsiret.text.strip()
        }

        # Définir les champs obligatoires
        required_fields = {
            'nom': 'Nom du Client',
            'adresse': 'Adresse',
            'cp': 'Code Postal',
            'pays': 'Pays'
        }

        # Vérifier les champs obligatoires
        missing_fields = []
        for field, field_name in required_fields.items():
            if not client_data[field]:
                missing_fields.append(field_name)

        if missing_fields:
            self.show_message(f"Les champs suivants sont obligatoires :\n{', '.join(missing_fields)}")
            return

        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            client_data['id'] = self.client_id
            cursor.execute('''
                UPDATE Clients 
                SET nom = :nom,
                    adresse = :adresse,
                    CP = :cp,
                    pays = :pays,
                    email = :email,
                    ntva = :ntva,
                    nsiret = :nsiret
                WHERE id_client = :id
            ''', client_data)

            conn.commit()
            conn.close()

            def on_popup_dismiss():
                self.manager.current = 'mes_clients'

            self.show_message(
                "Les informations du client ont bien été mises à jour",
                callback=on_popup_dismiss
            )
            
        except sqlite3.Error as e:
            error_msg = f"Erreur lors de la modification : {e}"
            print(error_msg)
            self.show_message(error_msg)

    def return_to_clients(self):
        """Retourne à la liste des clients"""
        self.manager.current = 'mes_clients'



# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'modifier_client.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)