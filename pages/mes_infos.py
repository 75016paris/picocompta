from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import ObjectProperty
import os
import sqlite3
from utils import resource_path

class MesInfosPage(Screen):
    # Define properties for all widgets, including the newly added ones
    info_nom = ObjectProperty(None)
    info_prenom = ObjectProperty(None)
    info_adresse = ObjectProperty(None)
    info_CP = ObjectProperty(None)
    info_pays = ObjectProperty(None)
    info_email = ObjectProperty(None)
    info_telephone = ObjectProperty(None)
    info_nsiret = ObjectProperty(None)
    info_codeape = ObjectProperty(None)
    info_nss = ObjectProperty(None)
    info_ntva = ObjectProperty(None)
    info_rib = ObjectProperty(None)
    info_iban = ObjectProperty(None)
    info_bic = ObjectProperty(None)
    info_activite_principal = ObjectProperty(None)
    info_echeance_declaration = ObjectProperty(None)
    info_dernier_numero_facture = ObjectProperty(None)

    def on_pre_enter(self):
        """Load information from the database before displaying the page."""
        self.charger_infos()

    def charger_infos(self):
        """Load personal information from the database and pre-fill the fields."""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Retrieve the latest personal information entry from the database
            cursor.execute('''
                SELECT nom, prenom, adresse, CP, pays, email, telephone, nsiret, codeape, 
                       nss, ntva, rib, iban, bic, activite_principal, echeance_declaration, dernier_numero_facture
                FROM Info_Personnelle
                ORDER BY id_personnelle DESC
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            if row:
                # Update the fields with data from the database
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
                self.ids.activite_principal.text = str(row[14] or '')
                
                # Set echeance_declaration based on the value in the database
                if row[15] == 1:
                    self.ids.echeance_declaration.text = "1 mois"
                elif row[15] == 3:
                    self.ids.echeance_declaration.text = "3 mois"
                else:
                    self.ids.echeance_declaration.text = "Sélectionner"

                self.ids.dernier_numero_facture.text = str(row[16] or '0')
            
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des informations : {e}")

    def modifier_infos(self):
        """Redirect to the modification page with pre-filled information."""
        if hasattr(self.manager, 'get_screen'):
            modif_inscription_screen = self.manager.get_screen('modif_inscription')
            if hasattr(modif_inscription_screen, 'pre_remplir_infos'):
                # Pass all information to the modification screen for pre-filling
                modif_inscription_screen.pre_remplir_infos(
                    nom=self.ids.nom.text,
                    prenom=self.ids.prenom.text,
                    adresse=self.ids.adresse.text,
                    CP=self.ids.CP.text,
                    pays=self.ids.pays.text,
                    email=self.ids.email.text,
                    telephone=self.ids.telephone.text,
                    nsiret=self.ids.nsiret.text,
                    codeape=self.ids.codeape.text,
                    nss=self.ids.nss.text,
                    ntva=self.ids.ntva.text,
                    rib=self.ids.rib.text,
                    iban=self.ids.iban.text,
                    bic=self.ids.bic.text,
                    activite_principal=self.ids.activite_principal.text,
                    echeance_declaration=self.ids.echeance_declaration.text,
                    dernier_numero_facture=self.ids.dernier_numero_facture.text
                )
            self.manager.current = 'modif_inscription'


# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'mes_infos.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)