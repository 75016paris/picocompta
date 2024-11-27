from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.lang import Builder

import os
import sys

generated_pdfs_path = os.path.join(os.path.dirname(__file__), 'generated_pdfs')
if not os.path.exists(generated_pdfs_path):
    os.makedirs(generated_pdfs_path)

def resource_path(relative_path):
    """Obtenir le chemin absolu vers les ressources, en tenant compte de PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

print(sys.path)
print("Python executable:", sys.executable)
print("Python version:", sys.version)

# Load the global style file
style_path = resource_path('assets/style.kv')
if os.path.exists(style_path):
    try:
        Builder.load_file(style_path)
        print(f"Global style file 'style.kv' loaded from: {style_path}")
    except Exception as e:
        print(f"Error loading 'style.kv': {e}")
else:
    print(f"Error: 'style.kv' file not found at {style_path}")

# Import screens
from pages.demarrage import DemarragePage
from pages.home import HomePage
from pages.inscription import InscriptionPage
from pages.nouveau_client import NouveauClientPage
from pages.mes_factures import MesFacturesPage
from pages.mes_clients import MesClientsPage
from pages.URSSAF_TVA import URSSAF_TVAPage
from pages.mes_infos import MesInfosPage
from pages.modifier_client import ModifierClientPage
from pages.nouvelle_facture import NouvelleFacturePage
from pages.modification_facture import ModificationFacturePage
from pages.modif_inscription import ModifInscriptionPage

class MainApp(App):
    def build(self):
        print("Building ScreenManager")
        sm = ScreenManager()
        
        # Define pages and add them to the screen manager
        pages = [
            DemarragePage(name='demarrage'),
            HomePage(name='home'),
            InscriptionPage(name='inscription'),
            NouvelleFacturePage(name='nouvelle_facture'),
            NouveauClientPage(name='nouveau_client'),
            MesFacturesPage(name='mes_factures'),
            MesClientsPage(name='mes_clients'),
            URSSAF_TVAPage(name='URSSAF_TVA'),
            MesInfosPage(name='mes_infos'),
            ModifierClientPage(name='modifier_client'),
            ModifInscriptionPage(name='modif_inscription'),
            ModificationFacturePage(name='modification_facture')
        ]
        
        # Add each page with debugging information
        for page in pages:
            sm.add_widget(page)
            print(f"Page '{page.name}' added to ScreenManager")
        
        # Set the initial screen
        sm.current = 'demarrage'
        print("Initial screen set to 'demarrage'")
        
        return sm

# Initialize and run the app
if __name__ == '__main__':
    print("Starting the application")

    # Initialize the database
    from db.database_utils import init_database
    if init_database():
        print("Database initialized successfully.")
    else:
        print("Database initialization failed.")

    # Run the Kivy application
    MainApp().run()