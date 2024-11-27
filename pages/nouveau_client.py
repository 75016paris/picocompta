from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
import os
import sqlite3
from utils import resource_path

class NouveauClientPage(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client_id = None

    def on_pre_enter(self):
        """Réinitialise les champs quand on entre dans la page"""
        if not self.client_id:  # Si pas d'ID client, c'est une création
            self.reset_fields()
            self.ids.page_title.text = "Nouveau Client"
            self.ids.save_button.text = "Sauvegarder"

    def reset_fields(self):
        """Réinitialise tous les champs"""
        self.client_id = None
        self.ids.nom.text = ""
        self.ids.adresse.text = ""
        self.ids.cp.text = ""
        self.ids.pays.text = ""
        self.ids.email.text = ""
        self.ids.ntva.text = ""
        self.ids.nsiret.text = ""

    def show_message(self, message, callback=None):
        """Display a popup message to the user with a 'Suivant' button."""
        
        # Create the popup content layout
        popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        message_label = Label(
            text=message,
            size_hint_y=None,
            height=100,
            text_size=(400, None),  # Définir une largeur maximale
            halign='center',
            valign='middle'
        )
        suivant_button = Button(text="Suivant", size_hint_y=None, height=40)

        # Bind the button to close the popup and execute the callback if provided
        suivant_button.bind(on_release=lambda instance: popup.dismiss())
        if callback:
            suivant_button.bind(on_release=lambda instance: callback())

        # Add message and button to popup content
        popup_content.add_widget(message_label)
        popup_content.add_widget(suivant_button)

        # Create the popup
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

        # Chemin de la base de données
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        
        try:
            # Connexion à la base de données
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            if self.client_id:  # Modification d'un client existant
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
            else:  # Création d'un nouveau client
                cursor.execute('''
                    INSERT INTO Clients 
                    (nom, adresse, CP, pays, email, ntva, nsiret)
                    VALUES 
                    (:nom, :adresse, :cp, :pays, :email, :ntva, :nsiret)
                ''', client_data)

            # Valider la transaction
            conn.commit()
            
            # Récupérer l'ID du client si c'est une création
            if not self.client_id:
                self.client_id = cursor.lastrowid
            
            # Fermer la connexion
            conn.close()

            print(f"Client {'modifié' if self.client_id else 'créé'} avec l'ID : {self.client_id}")

            def on_popup_dismiss():
                self.reset_fields()  # Réinitialiser les champs
                self.manager.current = 'mes_clients'

            self.show_message(
                "Les informations de la société on bien été enregistées",
                callback=on_popup_dismiss
            )
            
        except sqlite3.Error as e:
            error_msg = f"Erreur lors de l'opération : {e}"
            print(error_msg)
            self.show_message(error_msg)


# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'nouveau_client.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)