from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from datetime import datetime
import os
import sqlite3
from utils import resource_path

class ClientRow(BoxLayout):
    status = NumericProperty(0)
    all_declared = BooleanProperty(False)

    def __init__(self, client_data, parent_screen, **kwargs):
        super().__init__(**kwargs)
        self.parent_screen = parent_screen
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 40
        self.padding = 5
        self.spacing = 2
        
        # Statut pour la coloration
        self.status = 1 if client_data['impayes'] == 0 else 0
        self.all_declared = self.status == 1

        # Nom
        self.add_widget(Label(
            text=client_data['nom'],
            size_hint_x=0.2
        ))
        
        # Première facture
        date_str = client_data['premiere_facture'] or 'Aucune'
        self.add_widget(Label(
            text=date_str,
            size_hint_x=0.15
        ))
        
        # CA N
        self.add_widget(Label(
            text=f"{client_data['ca_n']:.2f} €",
            size_hint_x=0.15
        ))
        
        # CA Total
        self.add_widget(Label(
            text=f"{client_data['ca_total']:.2f} €",
            size_hint_x=0.15
        ))
        
        # Impayés
        self.add_widget(Label(
            text=f"{client_data['impayes']:.2f} €",
            size_hint_x=0.15
        ))
        
        # Bouton Modifier
        actions = BoxLayout(size_hint_x=0.2, spacing=5)
        modifier_btn = Button(
            text='Modifier',
            size_hint=(None, None),
            size=(60, 30),
            pos_hint={'center_y': 0.5},
            on_release=lambda x: self.modifier_client(client_data['id'])
        )
        actions.add_widget(modifier_btn)
        self.add_widget(actions)

    def get_background_color(self):
        return (0.7, 1, 0.7, 1) if self.all_declared else (1, 0.7, 0.7, 1)

    def modifier_client(self, client_id):
        """Redirige vers la modification du client"""
        modifier_screen = self.parent_screen.manager.get_screen('modifier_client')
        modifier_screen.charger_client(client_id)
        self.parent_screen.manager.current = 'modifier_client'

class MesClientsPage(Screen):
    tri_actuel = 'nom'
    ordre_croissant = True

    def on_enter(self):
        """Appelé quand on entre dans la page"""
        self.charger_clients()

    def charger_clients(self):
        """Charge et affiche la liste des clients"""
        # Vider la liste actuelle
        self.ids.clients_container.clear_widgets()
        
        # Connexion à la base de données
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Requête pour récupérer les clients avec leurs données
            query = '''
                SELECT 
                    c.id_client,
                    c.nom,
                    MIN(f.date_emission) as premiere_facture,
                    SUM(CASE 
                        WHEN strftime('%Y', f.date_emission) = strftime('%Y', 'now') 
                        THEN f.montant_total 
                        ELSE 0 
                    END) as ca_n,
                    SUM(f.montant_total) as ca_total,
                    SUM(CASE 
                        WHEN f.status = 0 
                        THEN f.montant_total 
                        ELSE 0 
                    END) as impayes
                FROM Clients c
                LEFT JOIN Factures f ON c.id_client = f.id_client
                GROUP BY c.id_client, c.nom
                ORDER BY 
                    CASE WHEN :tri = 'nom' THEN c.nom 
                         WHEN :tri = 'date' THEN premiere_facture 
                         WHEN :tri = 'ca_n' THEN ca_n 
                         WHEN :tri = 'ca_total' THEN ca_total 
                         WHEN :tri = 'impayes' THEN impayes 
                    END
            '''
            if not self.ordre_croissant:
                query += ' DESC'
            
            cursor.execute(query, {'tri': self.tri_actuel})
            
            for row in cursor.fetchall():
                client_data = {
                    'id': row[0],
                    'nom': row[1],
                    'premiere_facture': row[2],
                    'ca_n': row[3] or 0,
                    'ca_total': row[4] or 0,
                    'impayes': row[5] or 0
                }
                self.ids.clients_container.add_widget(ClientRow(client_data, self))
            
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Erreur lors du chargement des clients : {e}")

    def trier_par(self, critere):
        """Change le critère de tri et recharge la liste"""
        if critere == self.tri_actuel:
            self.ordre_croissant = not self.ordre_croissant
        else:
            self.tri_actuel = critere
            self.ordre_croissant = True
        self.charger_clients()


# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'mes_clients.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)