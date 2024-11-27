from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty, ObjectProperty
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from datetime import date
from db.database_utils import get_db_path
import os
import sqlite3
import platform
from utils import resource_path
import subprocess
import webbrowser


# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'mes_factures.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)

# Define the base directory for the entire project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generated_pdfs'))


class FactureRow(BoxLayout):
    status = NumericProperty(0)
    all_declared = BooleanProperty(False)
    background_color = ListProperty([1, 0.7, 0.7, 1])  # Default red

    def __init__(self, facture_data, modify_callback, parent_screen, **kwargs):
        super().__init__(**kwargs)
        self.parent_screen = parent_screen
        self.facture_id = facture_data['id']
        self.status = facture_data['status']
        self.all_declared = facture_data['status'] == 1
        
        # Update initial background color
        self._update_background_color()

        # Client name
        self.add_widget(Label(
            text=facture_data['client'],
            size_hint_x=0.15
        ))

        # Activity Type
        self.add_widget(Label(
            text=facture_data['type_activite'],
            size_hint_x=0.15
        ))

        # Invoice date
        self.add_widget(Label(
            text=facture_data['date'],
            size_hint_x=0.15
        ))

        # Montant HT
        self.add_widget(Label(
            text=f"{facture_data['montant_ht']:.2f} €",
            size_hint_x=0.15
        ))

        # TVA
        self.add_widget(Label(
            text=f"{facture_data['tva']:.2f} €",
            size_hint_x=0.1
        ))

        # Montant Total
        self.add_widget(Label(
            text=f"{facture_data['montant_total']:.2f} €",
            size_hint_x=0.15
        ))

        # Status as a Spinner
        self.status_spinner = Spinner(
            text='PAYÉ' if self.status == 1 else 'À PAYER',
            values=('PAYÉ', 'À PAYER'),
            size_hint_x=0.1,
            size_hint_y=None,
            height=30
        )
        self.status_spinner.bind(text=self.on_status_change)
        self.add_widget(self.status_spinner)

        # Actions buttons
        actions = BoxLayout(size_hint_x=0.2, spacing=5)
        view_btn = Button(
            text='Voir',
            size_hint_x=0.1,
            size_hint_y=None,
            height=30,  # Set height to match row elements
            pos_hint={'center_y': 0.5},  # Center vertically
            on_release=lambda x: self.view_facture_pdf(facture_data['id'], facture_data['client'])
        )
        modify_btn = Button(
            text='Modifier',
            size_hint_x=0.1,
            size_hint_y=None,
            height=30,  # Set height to match row elements
            pos_hint={'center_y': 0.5},  # Center vertically
            on_release=lambda x: modify_callback(facture_data['id'])
        )
        actions.add_widget(view_btn)
        actions.add_widget(modify_btn)
        self.add_widget(actions)

        # Bind the status property to the background color update
        self.bind(status=self._update_background_color)

    def _update_background_color(self, *args):
        """Update the background color based on status"""
        if self.status == 1:
            self.background_color = [0.7, 1, 0.7, 1]  # Light green for paid
        else:
            self.background_color = [1, 0.7, 0.7, 1]  # Light red for unpaid

    def on_status_change(self, spinner, text):
        is_paid = 1 if text == 'PAYÉ' else 0
        self.status = is_paid  # This will trigger _update_background_color
        self.all_declared = is_paid == 1
        self.update_status(self.facture_id, is_paid)

    def update_status(self, facture_id, is_paid):
        """Update the status in the database when spinner value changes"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            date_status_set = date.today().strftime('%Y-%m-%d') if is_paid else None
            cursor.execute("""
                UPDATE Factures
                SET status = ?, date_status_set = ?
                WHERE id_facture = ?
            """, (is_paid, date_status_set, facture_id))
            conn.commit()
            conn.close()
            print(f"Updated status for facture ID {facture_id} to {'Paid' if is_paid else 'Unpaid'}")
            
            # Force refresh of the parent screen
            if hasattr(self.parent_screen, 'charger_factures'):
                Clock.schedule_once(lambda dt: self.parent_screen.charger_factures(), 0.1)
                
        except sqlite3.Error as e:
            print(f"Error updating facture status: {e}")


    def view_facture_pdf(self, facture_id, client_name):
        """Open the PDF for the selected invoice based on ID and client name."""
        pdf_path = os.path.join(BASE_DIR, f"facture_{facture_id}_{client_name.replace(' ', '_')}.pdf")
        self.open_pdf(pdf_path)

    def open_pdf(self, pdf_path):
        """Opens a PDF file using the default viewer, based on the OS."""
        if not os.path.exists(pdf_path):
            print(f"PDF file not found at {pdf_path}")
            return

        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", pdf_path])
            elif platform.system() == "Windows":  # Windows
                os.startfile(pdf_path)
            elif platform.system() == "Linux":  # Linux
                subprocess.run(["xdg-open", pdf_path])
            else:  # Fallback for unknown platforms
                webbrowser.open(f'file://{pdf_path}')
        except Exception as e:
            print(f"Error opening PDF: {e}")

class MesFacturesPage(Screen):
    tri_actuel = 'date'
    ordre_croissant = True

    def on_enter(self):
        """Called when entering the page"""
        self.charger_factures()

    def charger_factures(self):
        """Load and display the list of invoices"""
        try:
            if 'factures_container' not in self.ids:
                raise AttributeError("factures_container ID not found in MesFacturesPage ids.")

            self.ids.factures_container.clear_widgets()
            
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    f.id_facture,
                    c.nom as client,
                    f.date_emission as date,
                    COALESCE(f.montant_htBICs, 0) + COALESCE(f.montant_htBICm, 0) + COALESCE(f.montant_htBNC, 0) as montant_ht,
                    f.tva,
                    f.montant_total,
                    f.status,
                    f.type_activite
                FROM Factures f
                JOIN Clients c ON f.id_client = c.id_client
                ORDER BY 
                    CASE WHEN :tri = 'client' THEN c.nom 
                         WHEN :tri = 'montant_ht' THEN (COALESCE(f.montant_htBICs, 0) + COALESCE(f.montant_htBICm, 0) + COALESCE(f.montant_htBNC, 0))
                         WHEN :tri = 'montant_total' THEN f.montant_total 
                         WHEN :tri = 'status' THEN f.status 
                         WHEN :tri = 'date' THEN f.date_emission
                    END
            '''
            if not self.ordre_croissant:
                query += ' DESC'
            
            cursor.execute(query, {'tri': self.tri_actuel})
            
            for row in cursor.fetchall():
                facture_data = {
                    'id': row[0],
                    'client': row[1],
                    'date': row[2],
                    'montant_ht': row[3],
                    'tva': row[4] or 0,
                    'montant_total': row[5] or 0,
                    'status': row[6],
                    'type_activite': row[7]
                }
                self.ids.factures_container.add_widget(
                    FactureRow(facture_data, self.modify_facture, self)
                )

            conn.close()
            
        except sqlite3.Error as e:
            print(f"Erreur lors du chargement des factures : {e}")
        except AttributeError as ae:
            print(f"Erreur d'attribut : {ae}")

    def modify_facture(self, facture_id):
        """Navigate to modification page for the selected invoice"""
        modification_screen = self.manager.get_screen('modification_facture')
        modification_screen.facture_id = facture_id
        self.manager.current = 'modification_facture'

    def trier_par(self, critere):
        """Change the sorting criteria and reload the list"""
        if critere == self.tri_actuel:
            self.ordre_croissant = not self.ordre_croissant
        else:
            self.tri_actuel = critere
            self.ordre_croissant = True
        self.charger_factures()

