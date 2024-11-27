from kivy.uix.screenmanager import Screen
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ObjectProperty
from kivy.lang import Builder
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex
from kivy.uix.textinput import TextInput
import sqlite3
import os
from datetime import datetime
from utils import resource_path


# Load the KV file
from kivy.lang import Builder

kv_file = resource_path(os.path.join('pages', 'URSSAF_TVA.kv'))
print(f"Chemin du fichier KV : {kv_file}")  # Optionnel, pour débogage
Builder.load_file(kv_file)

class URSSAF_TVAPage(Screen):
    selected_year = NumericProperty(datetime.now().year)
    echeance_declaration = NumericProperty(3)  # Default to quarterly
    urssaf_total_factures = NumericProperty(0)
    urssaf_total_ht = NumericProperty(0)
    urssaf_total_charge = NumericProperty(0)
    tva_total_factures = NumericProperty(0)
    tva_total_ht = NumericProperty(0)
    tva_total_tva = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_user_preferences()
        self.load_data()

    def on_enter(self):
        """Refresh page data when entered"""
        self.load_data()

    def load_user_preferences(self):
        db_path = self.get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT echeance_declaration FROM Info_personnelle ORDER BY id_personnelle DESC LIMIT 1")
        result = cursor.fetchone()
        self.echeance_declaration = result[0] if result else 3
        conn.close()

    def load_data(self):
        self.ids.urssaf_container.clear_widgets()
        self.ids.tva_container.clear_widgets()

        periods = self.generate_periods()
        for period in periods:
            self._add_urssaf_row(period)
            self._add_tva_row(period)
        
        self.update_totals()

    def _add_urssaf_row(self, period):
        period_label = f"{period['name']} {self.selected_year}"
        urssaf_data = self.calculate_urssaf_data(period['start_date'], period['end_date'])
        
        row_color = self.get_row_color(period['start_date'], period['end_date'], urssaf_data['all_declared'], is_tva=False)

        urssaf_row = PeriodRow(
            period_label=period_label,
            nb_factures=urssaf_data['nb_factures'],
            total_ht=urssaf_data['total_ht'],
            total_charge=urssaf_data['total_charge'],
            all_declared=urssaf_data['all_declared'],
            row_color=row_color,
            details_callback=lambda p=period, d=urssaf_data: self.show_details("URSSAF", p, d)
        )
        self.ids.urssaf_container.add_widget(urssaf_row)

    def _add_tva_row(self, period):
        period_label = f"{period['name']} {self.selected_year}"
        tva_data = self.calculate_tva_data(period['start_date'], period['end_date'])
        
        row_color = self.get_row_color(period['start_date'], period['end_date'], tva_data['all_declared'], is_tva=True)

        tva_row = PeriodRow(
            period_label=period_label,
            nb_factures=tva_data['nb_factures'],
            total_ht=tva_data['total_ht'],
            total_tva=tva_data['total_tva'],
            all_declared=tva_data['all_declared'],
            row_color=row_color,
            details_callback=lambda p=period: self.show_details("TVA", p, None)
        )
        self.ids.tva_container.add_widget(tva_row)

    def get_db_path(self):
        """Return the path to the database."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')

    def get_row_color(self, start_date, end_date, all_declared, is_tva=False):
        """Determine row color based on the period status and dates"""
        try:
            db_path = self.get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Retrieve the activity start dates and TVA status
            cursor.execute("""
                SELECT debut_activite, debut_activite_TVA, status_tva
                FROM Info_Personnelle 
                ORDER BY id_personnelle DESC LIMIT 1
            """)
            result = cursor.fetchone()

            # If no result, initialize with default values
            if not result:
                debut_activite, debut_activite_tva, status_tva = None, None, None
            else:
                debut_activite = datetime.strptime(result[0], "%Y-%m-%d").date() if result[0] else None
                debut_activite_tva = datetime.strptime(result[1], "%Y-%m-%d").date() if result[1] else None
                status_tva = result[2]

            # Pour les lignes TVA, vérifier d'abord le status_tva
            if is_tva:
                if not status_tva:
                    return "gray"
                    
            # Convert dates for comparison
            current_date = datetime.now().date()
            period_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            period_end = datetime.strptime(end_date, "%Y-%m-%d").date()

            # Check if this is the current period
            if period_start <= current_date <= period_end:
                return "blue"

            # Vérifier les autres conditions pour TVA et URSSAF
            if is_tva:
                if not debut_activite_tva or period_start < debut_activite_tva or period_start > current_date:
                    return "gray"
            else:
                if not debut_activite or period_start < debut_activite or period_start > current_date:
                    return "gray"

            # Check declarations for past periods
            if all_declared:
                return "green"
            return "red"

        except (sqlite3.Error, ValueError) as e:
            print(f"Error in get_row_color: {e}")
            return "red"
        finally:
            if conn:
                conn.close()

    def update_totals(self):
        """Update URSSAF and TVA totals"""
        self.urssaf_total_factures = sum(child.nb_factures for child in self.ids.urssaf_container.children)
        self.urssaf_total_ht = sum(child.total_ht for child in self.ids.urssaf_container.children)
        self.urssaf_total_charge = sum(child.total_charge for child in self.ids.urssaf_container.children)
        self.tva_total_factures = sum(child.nb_factures for child in self.ids.tva_container.children)
        self.tva_total_ht = sum(child.total_ht for child in self.ids.tva_container.children)
        self.tva_total_tva = sum(child.total_tva for child in self.ids.tva_container.children)

    def generate_periods(self):
        if self.echeance_declaration == 3:  # Quarterly
            return [
                {"name": "1er Trimestre", "start_date": f"{self.selected_year}-01-01", "end_date": f"{self.selected_year}-03-31"},
                {"name": "2ème Trimestre", "start_date": f"{self.selected_year}-04-01", "end_date": f"{self.selected_year}-06-30"},
                {"name": "3ème Trimestre", "start_date": f"{self.selected_year}-07-01", "end_date": f"{self.selected_year}-09-30"},
                {"name": "4ème Trimestre", "start_date": f"{self.selected_year}-10-01", "end_date": f"{self.selected_year}-12-31"}
            ]
        else:  # Monthly
            return [
                {
                    "name": ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"][month - 1],
                    "start_date": f"{self.selected_year}-{month:02d}-01",
                    "end_date": f"{self.selected_year}-{month:02d}-{self.days_in_month(month)}"
                }
                for month in range(1, 13)
            ]

    def days_in_month(self, month):
        if month in [4, 6, 9, 11]:
            return 30
        elif month == 2:
            return 29 if self.selected_year % 4 == 0 else 28
        return 31

    def calculate_urssaf_data(self, start_date, end_date):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Vérifier déclaration à zéro
            cursor.execute("""
                SELECT COUNT(*) FROM Declarations_Zero 
                WHERE type = 'URSSAF' 
                AND date_debut = ? 
                AND date_fin = ?
            """, (start_date, end_date))
            zero_declaration = cursor.fetchone()[0] > 0

            cursor.execute("""
                SELECT COUNT(*) as total_factures,
                    SUM(montant_ht) as total_ht,
                    type_activite,
                    MIN(CASE WHEN status_declaration_URSSAF = 1 THEN 1 ELSE 0 END) as all_declared,
                    taux_BNC, taux_BICm, taux_BICs
                FROM Factures
                WHERE date_emission BETWEEN ? AND ? AND status = 1
                GROUP BY type_activite
            """, (start_date, end_date))
            rows = cursor.fetchall()

            totals = {
                "nb_factures": 0,
                "total_ht": 0,
                "total_charge": 0,
                "total_bnc": 0,
                "total_bicm": 0,
                "total_bics": 0,
                "all_declared": True
            }

            if not rows:
                totals["all_declared"] = zero_declaration
                return totals

            for row in rows:
                nb_factures, montant_ht, activity_type, declared_status, taux_bnc, taux_bicm, taux_bics = row
                montant_ht = montant_ht or 0
                charge = 0

                totals["nb_factures"] += nb_factures or 0
                totals["total_ht"] += montant_ht

                if activity_type == 'BNC':
                    charge = montant_ht * (taux_bnc or 0.22)
                    totals["total_bnc"] += charge
                elif activity_type == 'BIC marchandise':
                    charge = montant_ht * (taux_bicm or 0.13)
                    totals["total_bicm"] += charge
                elif activity_type == 'BIC service':
                    charge = montant_ht * (taux_bics or 0.245)
                    totals["total_bics"] += charge

                totals["total_charge"] += charge
                if not declared_status:
                    totals["all_declared"] = False

            totals["all_declared"] = totals["all_declared"] or zero_declaration
            return totals

    def calculate_tva_data(self, start_date, end_date):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*), SUM(montant_ht), SUM(tva), MIN(status_declaration_TVA) AS all_declared
                FROM Factures
                WHERE date_emission BETWEEN ? AND ? AND status = 1
            """, (start_date, end_date))
            row = cursor.fetchone()

        return {
            "nb_factures": row[0] or 0,
            "total_ht": row[1] or 0,
            "total_tva": row[2] or 0,
            "all_declared": bool(row[3])
        }

    def show_details(self, type_declaration, period, data):
        if type_declaration == "URSSAF":
            popup = URSSAFDetailsPopup(period=period, data=data, refresh_callback=self.load_data)
        else:
            popup = TVADetailsPopup(period=period, refresh_callback=self.load_data)
        popup.open()

    def change_year(self, direction):
        self.selected_year += direction
        self.load_data()

    def go_home(self):
        self.manager.current = 'home'

class PeriodRow(BoxLayout):
    period_label = StringProperty()
    nb_factures = NumericProperty()
    total_ht = NumericProperty()
    total_charge = NumericProperty()
    total_tva = NumericProperty()
    all_declared = BooleanProperty()
    details_callback = ObjectProperty()
    row_color = StringProperty("red")  # Default color

    def get_background_color(self):
        """Determine background color based on the row color value."""
        if self.row_color == "green":
            return (0.7, 1, 0.7, 1)  # Light green
        elif self.row_color == "blue":
            return (0.7, 0.7, 1, 1)  # Light blue
        elif self.row_color == "gray":
            return (0.8, 0.8, 0.8, 1)  # Light gray
        elif self.row_color == "red":
            return (1, 0.7, 0.7, 1)  # Light red
        return (1, 1, 1, 1)  # White by default
    
class BaseDetailsPopup(Popup):
    def __init__(self, period, refresh_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.period = period
        self.refresh_callback = refresh_callback
        self.size_hint = (0.9, 0.9)
        self.declaration_type = None  # 'URSSAF' ou 'TVA' à définir dans les sous-classes
        self.content = self.build_content()

    def build_content(self):
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        self._add_header(layout)
        self._add_data_grid(layout)
        self._add_summary(layout)
        self._add_buttons(layout)
        return layout

    def _add_header(self, layout):
        raise NotImplementedError("Subclasses must implement _add_header")

    def _add_data_grid(self, layout):
        raise NotImplementedError("Subclasses must implement _add_data_grid")

    def _add_summary(self, layout):
        raise NotImplementedError("Subclasses must implement _add_summary")

    def _add_buttons(self, layout):
        button_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)

        # Check if the period has ended
        if self.is_period_ended():
            declare_button = Button(text="Déclarer et Payer", on_press=self.declare_period)
        else:
            declare_button = Button(text="Vous pourrez déclarer après la fin de la période", disabled=True)
        
        close_button = Button(text="Retour", on_press=self.dismiss)
        button_layout.add_widget(declare_button)
        button_layout.add_widget(close_button)
        layout.add_widget(button_layout)

    def _add_buttons(self, layout):
        button_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)

        # Check if the period has ended
        if self.is_period_ended():
            # Récupérer le nombre de factures pour la période
            nb_factures = self.get_nb_factures()
            
            declare_button = Button(
                text="Déclarer et Payer",
                on_press=self.declare_period,
                disabled=nb_factures == 0  # Désactivé s'il n'y a pas de factures
            )
            
            declare_zero_button = Button(
                text="Déclarer à zéro",
                on_press=self.declare_zero_period,
                disabled=nb_factures > 0  # Désactivé s'il y a des factures
            )
            
            button_layout.add_widget(declare_button)
            button_layout.add_widget(declare_zero_button)
        else:
            declare_button = Button(
                text="Vous pourrez déclarer après la fin de la période",
                disabled=True
            )
            button_layout.add_widget(declare_button)
        
        close_button = Button(text="Retour", on_press=self.dismiss)
        button_layout.add_widget(close_button)
        layout.add_widget(button_layout)

    def get_nb_factures(self):
        """Récupère le nombre de factures pour la période"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM Factures
                    WHERE date_emission BETWEEN ? AND ?
                    AND status = 1
                """, (self.period['start_date'], self.period['end_date']))
                return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
    

    def declare_zero_period(self, instance):
        """Déclare directement la période à zéro sans popup"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Declarations_Zero (type, date_debut, date_fin, commentaire)
                VALUES (?, ?, ?, ?)
            """, (self.declaration_type, self.period['start_date'], self.period['end_date'], 'Déclaration à zéro'))
            conn.commit()
            
        if self.refresh_callback:
            self.refresh_callback()
        self.dismiss()

    def is_period_ended(self):
        """Check if the period has ended based on the current date."""
        end_date = datetime.strptime(self.period['end_date'], '%Y-%m-%d')  # Corrected this line
        return datetime.now() > end_date

    def declare_period(self, instance):
        """Method to handle the declaration of the period (to be overridden)."""
        raise NotImplementedError("Subclasses must implement declare_period")

class URSSAFDetailsPopup(BaseDetailsPopup):
    def __init__(self, period, data, **kwargs):
        # Ensure that period is correctly passed and assigned
        self.period = period  # Assign period to self before calling super
        self.data = data  # Assign data before calling super
        super().__init__(period=period, **kwargs)  # Pass period explicitly to the superclass

        self.declaration_type = "URSSAF"
        self.title = f"URSSAF Détails - {self.period['name']}"

    def _calculate_charge(self, montant_ht, type_activite, taux_bnc, taux_bicm, taux_bics):
        if type_activite == 'BNC':
            return montant_ht * (taux_bnc or 0.22)
        elif type_activite == 'BIC marchandise':
            return montant_ht * (taux_bicm or 0.13)
        elif type_activite == 'BIC service':
            return montant_ht * (taux_bics or 0.245)
        return 0

    def _add_header(self, layout):
        header_layout = GridLayout(cols=6, size_hint_y=None, height=40, spacing=5)
        headers = ["Client", "N°", "Date Paiement", "Montant HT", "Type d'activité", "Charge URSSAF"]
        for header in headers:
            header_layout.add_widget(Label(text=header, bold=True))
        layout.add_widget(header_layout)

    def _add_data_grid(self, layout):
        scroll = ScrollView(size_hint=(1, 0.6))
        grid = GridLayout(cols=6, size_hint_y=None, spacing=5, row_default_height=40)
        grid.bind(minimum_height=grid.setter('height'))

        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.nom, f.numero_facture, f.date_status_set, 
                       f.montant_ht, f.type_activite,
                       f.taux_BNC, f.taux_BICm, f.taux_BICs
                FROM Factures f
                JOIN Clients c ON f.id_client = c.id_client
                WHERE f.date_emission BETWEEN ? AND ?
                  AND f.status = 1
                ORDER BY f.date_emission
            """, (self.period['start_date'], self.period['end_date']))
            
            for row in cursor.fetchall():
                nom, num_facture, date, montant_ht, type_activite, taux_bnc, taux_bicm, taux_bics = row
                charge = self._calculate_charge(montant_ht, type_activite, taux_bnc, taux_bicm, taux_bics)
                
                for text in [str(nom), str(num_facture), str(date), f"{montant_ht:.2f} €", 
                           str(type_activite), f"{charge:.2f} €"]:
                    label = Label(
                        text=text,
                        size_hint_y=None,
                        height=40,
                        text_size=(None, None)
                    )
                    grid.add_widget(label)

        scroll.add_widget(grid)
        layout.add_widget(scroll)

    def declare_period(self, instance):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Factures
                SET status_declaration_URSSAF = 1
                WHERE date_emission BETWEEN ? AND ? AND status = 1
            """, (self.period['start_date'], self.period['end_date']))
            conn.commit()
        
        if self.refresh_callback:
            self.refresh_callback()
        self.dismiss()

    def _add_summary(self, layout):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        
        # Initialize totals dictionary for clarity
        totals = {
            'BNC': 0,
            'BIC marchandise': 0,
            'BIC service': 0
        }
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT type_activite, SUM(montant_ht) as total_ht
                    FROM Factures
                    WHERE date_emission BETWEEN ? AND ? 
                    AND status = 1
                    GROUP BY type_activite
                """, (self.period['start_date'], self.period['end_date']))
                
                # Update totals based on the activity type
                for type_activite, montant in cursor.fetchall():
                    if type_activite in totals:
                        totals[type_activite] = montant or 0  # Set montant to 0 if None

        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des totaux: {e}")

        # Create the summary layout
        summary = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=5)
        summary.add_widget(Label(text="À déclarer:", bold=True))
        summary.add_widget(Label(text=f"Recettes profession libérale (CIPAV): {totals['BNC']:.2f} €"))
        summary.add_widget(Label(text=f"CA ventes marchandises: {totals['BIC marchandise']:.2f} €"))
        summary.add_widget(Label(text=f"CA prestations services: {totals['BIC service']:.2f} €"))

        # Retrieve `total_charge` safely from `self.data`
        total_charge = self.data.get('total_charge', 0) if self.data else 0
        summary.add_widget(Label(text="À Payer:", bold=True))
        summary.add_widget(Label(text=f"Total des charges: {total_charge:.2f} €"))

        # Add the summary layout to the main layout
        layout.add_widget(summary)

    def declare_period(self, instance):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Factures
                SET status_declaration_URSSAF = 1
                WHERE date_emission BETWEEN ? AND ? AND status = 1
            """, (self.period['start_date'], self.period['end_date']))
            conn.commit()
        
        if self.refresh_callback:
            self.refresh_callback()
        self.dismiss()

class TVADetailsPopup(BaseDetailsPopup):
    def __init__(self, period, refresh_callback=None, **kwargs):
        super().__init__(period=period, refresh_callback=refresh_callback, **kwargs)
        self.declaration_type = "TVA"
        self.title = f"TVA Détails - {self.period['name']}"
        
    def _add_data_grid(self, layout):
        scroll = ScrollView(size_hint=(1, 0.6))
        grid = GridLayout(cols=5, size_hint_y=None, spacing=5, row_default_height=40)
        grid.bind(minimum_height=grid.setter('height'))

        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.nom, f.numero_facture, f.date_status_set, 
                           COALESCE(f.montant_ht, 0) as montant_ht, 
                           COALESCE(f.tva, 0) as tva
                    FROM Factures f
                    JOIN Clients c ON f.id_client = c.id_client
                    WHERE f.date_emission BETWEEN ? AND ?
                      AND f.status = 1
                    ORDER BY f.date_emission
                """, (self.period['start_date'], self.period['end_date']))
                
                rows = cursor.fetchall()
                
                if not rows:  # Si pas de données, ajouter une ligne vide
                    grid.add_widget(Label(text="Aucune facture pour cette période", size_hint_y=None, height=40))
                else:
                    for row in rows:
                        nom, num_facture, date, montant_ht, tva = row
                        for text in [str(nom or ''), str(num_facture or ''), str(date or ''), 
                                   f"{montant_ht:.2f} €", f"{tva:.2f} €"]:
                            label = Label(
                                text=text,
                                size_hint_y=None,
                                height=40,
                                text_size=(None, None)
                            )
                            grid.add_widget(label)

        except sqlite3.Error as e:
            grid.add_widget(Label(text=f"Erreur de chargement des données: {e}", size_hint_y=None, height=40))

        scroll.add_widget(grid)
        layout.add_widget(scroll)

    def _add_summary(self, layout):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(montant_ht), 0) as total_ht,
                        COALESCE(SUM(tva), 0) as total_tva
                    FROM Factures
                    WHERE date_emission BETWEEN ? AND ? 
                    AND status = 1
                """, (self.period['start_date'], self.period['end_date']))
                
                total_ht, total_tva = cursor.fetchone()
                
                # Garantir que les valeurs ne sont pas None
                total_ht = total_ht or 0
                total_tva = total_tva or 0

        except sqlite3.Error:
            total_ht = 0
            total_tva = 0

        summary = BoxLayout(orientation="vertical", size_hint_y=None, height=100, spacing=5)
        summary.add_widget(Label(text="Récapitulatif TVA:", bold=True))
        summary.add_widget(Label(text=f"Total HT: {total_ht:.2f} €"))
        summary.add_widget(Label(text=f"Total TVA à déclarer: {total_tva:.2f} €"))
        layout.add_widget(summary)

    def _add_header(self, layout):
        header_layout = GridLayout(cols=5, size_hint_y=None, height=40, spacing=5)
        headers = ["Client", "N° de Facture", "Date Paiement", "Montant HT", "TVA"]
        for header in headers:
            header_layout.add_widget(Label(text=header, bold=True))
        layout.add_widget(header_layout)
        
    def declare_period(self, instance):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Factures
                SET status_declaration_TVA = 1
                WHERE date_emission BETWEEN ? AND ? AND status = 1
            """, (self.period['start_date'], self.period['end_date']))
            conn.commit()
        
        if self.refresh_callback:
            self.refresh_callback()
        self.dismiss()

    def declare_period(self, instance):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'picocompta.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Factures
                SET status_declaration_TVA = 1
                WHERE date_emission BETWEEN ? AND ? AND status = 1
            """, (self.period['start_date'], self.period['end_date']))
            conn.commit()
        
        if self.refresh_callback:
            self.refresh_callback()
        self.dismiss()