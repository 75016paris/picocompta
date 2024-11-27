from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from db.database_utils import get_db_path
from datetime import datetime
import sqlite3
from utils import resource_path

class InvoicePDFGenerator:
    def __init__(self, db_path=None):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.db_path = db_path if db_path else get_db_path()

    def _setup_custom_styles(self):
        """Set up custom styles for the PDF."""
        self.styles.add(ParagraphStyle(
            name='RightAlign',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT
        ))
        self.styles.add(ParagraphStyle(
            name='Center',
            parent=self.styles['Normal'],
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading1'],
            alignment=TA_CENTER,
            spaceAfter=10  # Reduced spacing for closer alignment
        ))
        self.styles.add(ParagraphStyle(
            name='Bold',
            parent=self.styles['Normal'],
            fontName="Helvetica-Bold"
        ))
        self.styles.add(ParagraphStyle(
            name='SmallNormal',
            parent=self.styles['Normal'],
            fontSize=10  # Smaller font size specifically for "FACTURER À :"
        ))

    def generate_invoice(self, invoice_id, output_path):
        invoice_data = self._fetch_invoice_data(invoice_id)
        if not invoice_data:
            print(f"Facture avec ID {invoice_id} introuvable.")
            return

        # Check if ntva is NULL and raise an alert if necessary
        if invoice_data['client_ntva'] is None:
            self.show_alert("Vous devez renseigner le champ Numéro de TVA pour ce client, rendez-vous dans Mes Clients > Modifier > Numéro de TVA.")
            return

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        story = []
        story.extend(self._build_header(invoice_data))
        story.extend(self._build_recipient_block(invoice_data))
        story.extend(self._build_details(invoice_data))
        story.extend(self._build_amounts(invoice_data))
        story.extend(self._build_payment_info(invoice_data))

        doc.build(story)

    def _fetch_invoice_data(self, invoice_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    Factures.id_facture, Factures.date_emission, Factures.date_echeance, 
                    Factures.montant_htBICs, Factures.montant_htBICm, Factures.montant_htBNC, 
                    Factures.tva, Factures.montant_total, Clients.nom, Clients.adresse, 
                    Clients.pays, Clients.CP, Clients.ntva, Clients.nsiret, 
                    Info_Personnelle.nom, Info_Personnelle.prenom, Info_Personnelle.adresse, 
                    Info_Personnelle.CP, Info_Personnelle.pays, Info_Personnelle.nsiret, 
                    Info_Personnelle.codeape, Info_Personnelle.nss, Info_Personnelle.ntva, 
                    Info_Personnelle.telephone, Info_Personnelle.email,
                    Info_Personnelle.rib, Info_Personnelle.iban, Info_Personnelle.bic, 
                    Factures.mission, Factures.tva_status, Factures.taux_tva, Factures.numero_facture
                FROM 
                    Factures 
                JOIN 
                    Clients ON Factures.id_client = Clients.id_client
                LEFT JOIN 
                    Info_Personnelle ON Info_Personnelle.id_personnelle = (SELECT MAX(id_personnelle) FROM Info_Personnelle)
                WHERE 
                    Factures.id_facture = ?
            ''', (invoice_id,))

            result = cursor.fetchone()

            if result:
                montant_ht = result[3] + result[4] + result[5]
                taux_tva = result[30]
                montant_tva = result[6]
                numero_facture = result[31]

                return {
                    'invoice_number': result[0],
                    'issue_date': result[1],
                    'due_date': result[2],
                    'amount_ht': montant_ht,
                    'tva': result[6],
                    'total_ttc': result[7],
                    'client_name': result[8],
                    'client_address': result[9],
                    'client_country': result[10],
                    'client_cp': result[11],
                    'client_ntva': result[12],
                    'client_siret': result[13],
                    'company_name': f"{result[14]} {result[15]}",
                    'company_address': result[16],
                    'company_cp': result[17],
                    'company_country': result[18],
                    'company_siret': result[19],
                    'company_ape': result[20],
                    'company_ss': result[21],
                    'company_vat': result[22],
                    'telephone': result[23],
                    'company_email': result[24],
                    'rib': result[25],
                    'iban': result[26],
                    'bic': result[27],
                    'mission': result[28],
                    'tva_status': result[29],
                    'taux_tva': taux_tva,
                    'montant_tva': montant_tva,
                    'numero_facture': numero_facture
                }
            return None

        except sqlite3.OperationalError as e:
            print(f"Erreur lors de l'accès à la base de données : {e}")
            return None

    def _build_header(self, invoice_data):
        elements = []
        elements.append(Paragraph(invoice_data['company_name'], self.styles['Heading1']))
        elements.append(Paragraph(f"{invoice_data['company_address']}, {invoice_data['company_cp']} {invoice_data['company_country']}", self.styles['Normal']))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(f"{invoice_data['company_email']}", self.styles['Normal']))
        elements.append(Paragraph(f"{invoice_data['telephone']}", self.styles['Normal']))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(f"<b>SIRET :</b> {invoice_data['company_siret']}", self.styles['Normal']))
        elements.append(Paragraph(f"<b>APE :</b> {invoice_data['company_ape']}", self.styles['Normal']))

        if invoice_data['company_ss'] is not None:
            elements.append(Paragraph(f"<b>N° S.S. :</b> {invoice_data['company_ss']}", self.styles['Normal']))

        # Ajouter le numéro de TVA de l'entreprise si TVA active
        if invoice_data['tva_status'] == 1:
            # Gérer le numéro de TVA avec une variable intermédiaire
            company_vat = invoice_data.get('company_vat', '')
            vat_display = company_vat if company_vat else "en cours d'attribution"
            elements.append(Paragraph(f"<b>N°TVA :</b> {vat_display}", self.styles['Normal']))
        
        elements.append(Spacer(1, 100))
        elements.append(Paragraph(f"FACTURE N° {invoice_data['numero_facture']}", self.styles['InvoiceTitle']))
        formatted_date = datetime.strptime(invoice_data['issue_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        elements.append(Paragraph(formatted_date, self.styles['Center']))
        elements.append(Spacer(1, 10))
        return elements

    def _build_recipient_block(self, invoice_data):
        elements = []
        elements.append(Paragraph("FACTURER À :", self.styles['SmallNormal']))
        elements.append(Paragraph(f"<b>{invoice_data['client_name']}</b>", self.styles['Normal']))
        elements.append(Paragraph(invoice_data['client_address'], self.styles['Normal']))
        elements.append(Paragraph(f"{invoice_data['client_cp']}", self.styles['Normal']))
        elements.append(Paragraph(f"{invoice_data['client_country']}", self.styles['Normal']))

        # Ajouter le numéro SIRET du client s'il existe
        if invoice_data.get('client_siret'):
            elements.append(Paragraph(f"SIRET : {invoice_data['client_siret']}", self.styles['Normal']))

        # Ajouter le numéro de TVA du client s'il existe
        if invoice_data['client_ntva']:
            elements.append(Paragraph(f"TVA : {invoice_data['client_ntva']}", self.styles['Normal']))
        
        elements.append(Spacer(1, 10))
        return elements

    def _build_details(self, invoice_data):
        elements = []
        # Mission details
        elements.append(Paragraph("<b>Objet :</b>", self.styles['Heading2']))
        elements.append(Paragraph(invoice_data['mission'], self.styles['Normal']))
        elements.append(Spacer(1, 20))
        return elements

    def _build_amounts(self, invoice_data):
        elements = []
        # Amount details with right-aligned amounts
        amounts_data = [
            ["Montant HT", Paragraph(f"{invoice_data['amount_ht']:.2f} €", self.styles['RightAlign'])],
        ]

        # Always show TVA line with rate from database
        tva_rate = float(invoice_data['taux_tva']) if isinstance(invoice_data['taux_tva'], str) else invoice_data['taux_tva']
        tva_amount = invoice_data['montant_tva']
        amounts_data.append([
            Paragraph(f"TVA ({tva_rate:.2f}%)", self.styles['Normal']),
            Paragraph(f"{tva_amount:.2f} €", self.styles['RightAlign'])
        ])

        # Add TOTAL TTC as the last row
        amounts_data.append([
            Paragraph("<b>TOTAL TTC</b>", self.styles['Bold']),
            Paragraph(f"<b>{invoice_data['total_ttc']:.2f} €</b>", self.styles['RightAlign'])
        ])

        # Create table with all amounts
        amounts_table = Table(amounts_data, colWidths=[300, 200])
        amounts_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),  # Add line above TOTAL TTC
            ('TOPPADDING', (0, -1), (-1, -1), 6),  # Add some padding above TOTAL TTC
        ]))
        elements.append(amounts_table)

        # Show TVA non applicable message only if montant_tva is 0
        if invoice_data['montant_tva'] == 0:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("TVA non applicable, article 293B du CGI", self.styles['Normal']))

        elements.append(Spacer(1, 30))
        return elements

    def _build_payment_info(self, invoice_data):
        elements = []
        elements.append(Paragraph("<b>Paiement à réception :</b>", self.styles['Bold']))
        if invoice_data['rib']:
            elements.append(Paragraph(f"RIB : {invoice_data['rib']}", self.styles['Normal']))
        if invoice_data['iban']:
            elements.append(Paragraph(f"IBAN : {invoice_data['iban']}", self.styles['Normal']))
        if invoice_data['bic']:
            elements.append(Paragraph(f"BIC : {invoice_data['bic']}", self.styles['Normal']))
        return elements

    def show_alert(self, message):
        """Displays an alert dialog with a message."""
        # Implement alert functionality, you can use a simple print or integrate with a GUI alert library
        print(message)  # Replace this with actual alert implementation for your application 