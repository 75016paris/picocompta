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
import datetime
from utils import resource_path

class ModifInscriptionPage(Screen):
    def on_pre_enter(self):
        """Charge les données existantes avant d'afficher la page."""
        self.charger_donnees()

    def charger_donnees(self):
        """Charge les données existantes depuis la base de données."""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Récupérer les dernières informations personnelles
            cursor.execute('''
                SELECT nom, prenom, adresse, CP, pays, email, telephone, 
                       nsiret, codeape, nss, ntva, rib, iban, bic,
                       activite_principal, echeance_declaration, dernier_numero_facture
                FROM Info_Personnelle
                ORDER BY id_personnelle DESC
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            if row:
                # Remplir les champs texte
                self.ids.nom.text = str(row[0] or '')
                self.ids.prenom.text = str(row[1] or '')
                self.ids.adresse.text = str(row[2] or '')
                self.ids.CP.text = str(row[3] or '')
                self.ids.pays.text = str(row[4] or '')
                self.ids.email.text = str(row[5] or '')
                self.ids.telephone.text = str(row[6] or '')
                self.ids.nsiret.text = str(row[7] or '')
                self.ids.codeape.text = str(row[8] or '')
                self.ids.nss.text = str(row[9] or '')
                self.ids.ntva.text = str(row[10] or '')
                self.ids.rib.text = str(row[11] or '')
                self.ids.iban.text = str(row[12] or '')
                self.ids.bic.text = str(row[13] or '')
                
                # Remplir les spinners
                activite = str(row[14] or '')
                if activite in ['BIC marchandise', 'BIC service', 'BNC']:
                    self.ids.activite_principal_spinner.text = activite
                else:
                    self.ids.activite_principal_spinner.text = 'Sélectionner'

                echeance = row[15]
                if echeance == 1:
                    self.ids.echeance_declaration_spinner.text = '1 mois'
                elif echeance == 3:
                    self.ids.echeance_declaration_spinner.text = '3 mois'
                else:
                    self.ids.echeance_declaration_spinner.text = 'Sélectionner'

                self.ids.dernier_numero_facture.text = str(row[16] or '0')
            
            conn.close()
        except sqlite3.Error as e:
            print(f"Erreur lors du chargement des données : {e}")
            self.show_message(f"Erreur lors du chargement des données : {e}")

    def get_text_or_hint(self, widget):
        """Return text if entered, otherwise None for required fields."""
        return widget.text.strip() if widget.text.strip() else None

    def save_info(self):
        """Met à jour les informations dans la base de données."""
        # Récupérer les valeurs des champs
        nom = self.get_text_or_hint(self.ids.nom)
        prenom = self.get_text_or_hint(self.ids.prenom)
        adresse = self.get_text_or_hint(self.ids.adresse)
        cp = self.get_text_or_hint(self.ids.CP)
        pays = self.get_text_or_hint(self.ids.pays)
        email = self.get_text_or_hint(self.ids.email)
        telephone = self.get_text_or_hint(self.ids.telephone)
        nsiret = self.get_text_or_hint(self.ids.nsiret)
        codeape = self.get_text_or_hint(self.ids.codeape)
        nss = self.get_text_or_hint(self.ids.nss)
        ntva = self.get_text_or_hint(self.ids.ntva)
        rib = self.get_text_or_hint(self.ids.rib)
        iban = self.get_text_or_hint(self.ids.iban)
        bic = self.get_text_or_hint(self.ids.bic)
        
        # Traitement des spinners
        activite_principal = None
        if self.ids.activite_principal_spinner.text != "Sélectionner":
            activite_principal = self.ids.activite_principal_spinner.text
            
        echeance_declaration = None
        if self.ids.echeance_declaration_spinner.text == "1 mois":
            echeance_declaration = 1
        elif self.ids.echeance_declaration_spinner.text == "3 mois":
            echeance_declaration = 3
            
        dernier_numero_facture = self.ids.dernier_numero_facture.text.strip() or 0

        # Vérification des champs obligatoires
        required_fields = {
            'Nom': nom,
            'Prénom': prenom,
            'Adresse': adresse,
            'Code Postal': cp,
            'SIRET': nsiret,
            'Code APE': codeape,
            'IBAN': iban,
            'BIC': bic,
            'Type d\'activité': activite_principal,
            'Échéance déclaration': echeance_declaration
        }

        missing_fields = [field for field, value in required_fields.items() if not value]

        if missing_fields:
            self.show_message(f"Champs obligatoires manquants :\n{', '.join(missing_fields)}")
            return

        # Mise à jour dans la base de données
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Récupérer le dernier ID
            cursor.execute('SELECT MAX(id_personnelle) FROM Info_Personnelle')
            latest_id = cursor.fetchone()[0]
            
            if latest_id:
                # Mise à jour avec des paramètres nommés
                query = '''
                    UPDATE Info_Personnelle 
                    SET nom = ?, prenom = ?, adresse = ?, CP = ?, pays = ?,
                        email = ?, telephone = ?, nsiret = ?, codeape = ?,
                        nss = ?, ntva = ?, rib = ?, iban = ?, bic = ?,
                        activite_principal = ?, echeance_declaration = ?,
                        dernier_numero_facture = ?
                    WHERE id_personnelle = ?
                '''
                
                cursor.execute(query, (
                    nom, prenom, adresse, cp, pays,
                    email, telephone, nsiret, codeape,
                    nss, ntva, rib, iban, bic,
                    activite_principal, echeance_declaration,
                    dernier_numero_facture, latest_id
                ))
                
                conn.commit()
                self.show_message("Informations mises à jour avec succès.", callback=lambda: setattr(self.manager, 'current', 'mes_infos'))
            else:
                self.show_message("Aucun enregistrement trouvé à mettre à jour.")
            
            conn.close()
        except sqlite3.Error as e:
            self.show_message(f"Erreur lors de la mise à jour : {e}")

    def show_message(self, message, callback=None):
        """Affiche un message popup à l'utilisateur."""
        popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        message_label = Label(text=message, size_hint_y=None, height=100)
        suivant_button = Button(text="Suivant", size_hint_y=None, height=40)

        suivant_button.bind(on_release=lambda instance: popup.dismiss())
        if callback:
            suivant_button.bind(on_release=lambda instance: callback())

        popup_content.add_widget(message_label)
        popup_content.add_widget(suivant_button)

        popup = Popup(title="Message", content=popup_content, size_hint=(0.8, 0.4), auto_dismiss=False)
        popup.open()


# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'modif_inscription.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)