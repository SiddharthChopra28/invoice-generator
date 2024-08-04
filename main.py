import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QTableWidget,
    QTableWidgetItem, QFrame, QPushButton, QCompleter
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

import json

import signal

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


import io
import platform
import copy
import os
from datetime import datetime

signal.signal(signal.SIGINT, signal.SIG_DFL)


COORDINATES = {
    "invoice_no": {"x":108, "y":737, "font":"Arial_Bold", "size":12.4, "color":"#00a0e3"},
    "date": {"x":80, "y":713, "font":"Arial_Bold", "size":12.4, "color":"#00a0e3"},
    "buyers_po_no": {"x":120, "y":678, "font":"Arial_Bold", "size":12.4, "color":"#00a0e3"},
    "contact_person": {"x":117, "y":650, "font":"Arial_Bold", "size":12.4, "color":"#00a0e3"},
    "billed_to": {"x":85, "y":605, "font":"Arial_Bold", "size":9, "color":"#2b2a29"},
    "billed_to_gstin": {"x":125, "y":553, "font":"Arial_Bold", "size":9, "color":"#2b2a29"},
    "shipped_to": {"x":310, "y":605, "font":"Arial_Bold", "size":9, "color":"#2b2a29"},
    "shipped_to_gstin": {"x":355, "y":553, "font":"Arial_Bold", "size":9, "color":"#2b2a29"},
    "LINE_GAP_ADDRESS": 12,
    "sno": {"x":48, "y":490, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "particulars": {"x":80, "y":490, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "hsn": {"x":280, "y":490, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "qty": {"x":330, "y":490, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "uom": {"x":375, "y":490, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "price": {"x":420, "y":490, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "igst%": {"x":465, "y":490, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "amount_before_tax": {"x":510, "y":490, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "LINE_GAP_MAIN_Y": 19.8,
    "total_amount_before_tax": {"x":500, "y":210, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "total_tax": {"x":500, "y":195, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "freight_charges": {"x":500, "y":175, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "round_off": {"x":500, "y":115, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "grand_total": {"x":500, "y":95, "font":"Arial_Bold", "size":9, "color":"#00a0e3"},
    "freight_disclaimer": {"x": 485, "y":156, "font":"Arial", "size":6.5, "color":"#2b2a29"}

}


def format_text(text, chars):
    words = text.split(' ')
    new_list = []
    counter = 0
    added_till = 0
    for n, word in enumerate(words):
        counter += (len(word)+1)

        if counter>=chars:
            new_list.append((' '.join(words[added_till:n+1])))
            added_till = n+1
            counter = 0

    if added_till != len(words):
        new_list.append(' '.join(words[added_till:]))
    # print(' '.join(words[0:]))
    # print(new_list)
    return new_list


class InvoiceForm(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Invoice Form")
        self.setGeometry(100, 100, 752, 700)

        self.data_dict = {}
        
        
        self.sn_autocomplete_list = [] #
        self.particulars_autocomplete_list = []
        self.hsn_code_autocomplete_list = []
        self.qty_autocomplete_list = [] #
        self.uom_autocomplete_list = []
        self.price_autocomplete_list = []
        self.igst_autocomplete_list = []

        self.invoice_autocomplete_list = [] #
        self.date_autocomplete_list = [] #
        self.po_autocomplete_list = [] 
        self.contact_autocomplete_list = []

        self.billed_to_autocomplete_list = []
        self.billed_to_gstin_autocomplete_list = []
        self.shipped_to_autocomplete_list = []
        self.shipped_to_gstin_autocomplete_list = []
        
        self.freight_charges_autocomplete_list = []     

        self.get_json_data()
        
        self.pdfmaker = PdfMaker()

        main_layout = QVBoxLayout()
        header_layout = QHBoxLayout()
        
        new_form_button = QPushButton("New Form")
        generate_form_button = QPushButton("Generate Form")
        new_form_button.clicked.connect(self.clear_inputs)
        generate_form_button.clicked.connect(self.generate_form)
        
        header_layout.addWidget(new_form_button)
        header_layout.addWidget(generate_form_button)
        
        title = QLabel("    Performa Invoice generator")
        title.setFont(QFont('Arial', 20, QFont.Bold))
        header_layout.addWidget(title, alignment=Qt.AlignRight)
        
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.create_header_section())
        main_layout.addWidget(self.create_billed_shipped_section())
        main_layout.addWidget(self.create_table_section())
        main_layout.addWidget(self.create_footer_section())

        self.setLayout(main_layout)

    def create_header_section(self):
        self.header_frame = QFrame()
        header_layout = QGridLayout()

        self.invoice_input = QLineEdit()
        self.date_input = QLineEdit()
        self.date_input.setText(datetime.today().strftime('%d/%m/%Y'))

        self.po_input = QLineEdit()
        self.contact_input = QLineEdit()

        self.setup_autocomplete(self.invoice_input, self.invoice_autocomplete_list)
        self.setup_autocomplete(self.date_input, self.date_autocomplete_list)
        self.setup_autocomplete(self.po_input, self.po_autocomplete_list)
        self.setup_autocomplete(self.contact_input, self.contact_autocomplete_list)

        header_layout.addWidget(QLabel("P. Invoice No.:"), 0, 0)
        header_layout.addWidget(self.invoice_input, 0, 1)
        header_layout.addWidget(QLabel("Date:"), 0, 2)
        header_layout.addWidget(self.date_input, 0, 3)

        header_layout.addWidget(QLabel("Buyer's PO No.:"), 1, 0)
        header_layout.addWidget(self.po_input, 1, 1)
        header_layout.addWidget(QLabel("Contact Person:"), 1, 2)
        header_layout.addWidget(self.contact_input, 1, 3)

        self.header_frame.setLayout(header_layout)
        return self.header_frame

    def create_billed_shipped_section(self):
        frame = QFrame()
        self.billed_to_line_edit = QLineEdit()
        self.billed_to_gstin_line_edit = QLineEdit()
        self.shipped_to_line_edit = QLineEdit()
        self.shipped_to_gstin_line_edit = QLineEdit()

        self.setup_autocomplete(self.billed_to_line_edit, self.billed_to_autocomplete_list)
        self.setup_autocomplete(self.billed_to_gstin_line_edit, self.billed_to_gstin_autocomplete_list)
        self.setup_autocomplete(self.shipped_to_line_edit, self.shipped_to_autocomplete_list)
        self.setup_autocomplete(self.shipped_to_gstin_line_edit, self.shipped_to_gstin_autocomplete_list)

        layout = QHBoxLayout()

        billed_to = QVBoxLayout()
        billed_to.addWidget(QLabel("Billed To"))
        billed_to.addWidget(self.billed_to_line_edit)
        billed_to.addWidget(QLabel("Buyer's GSTIN No.- Billed"))
        billed_to.addWidget(self.billed_to_gstin_line_edit)

        shipped_to = QVBoxLayout()
        shipped_to.addWidget(QLabel("Shipped To"))
        shipped_to.addWidget(self.shipped_to_line_edit)
        shipped_to.addWidget(QLabel("Buyer's GSTIN No.- Shipped"))
        shipped_to.addWidget(self.shipped_to_gstin_line_edit)

        layout.addLayout(billed_to)
        layout.addLayout(shipped_to)

        frame.setLayout(layout)
        return frame

    def create_table_section(self):
        self.table = QTableWidget(14, 7)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels(["S.NO", "PARTICULARS", "HSN CODE", "QTY.", "UOM", "PRICE", "@IGST%"])

        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 322)
        self.table.setColumnWidth(2, 75)
        self.table.setColumnWidth(3, 50)
        self.table.setColumnWidth(4, 55)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 60)


        self.setup_table_autocomplete()

        table_frame = QFrame()
        table_layout = QVBoxLayout()
        table_layout.addWidget(self.table)
        table_frame.setLayout(table_layout)
        return table_frame

    def setup_table_autocomplete(self):
        column_completers = [
            QCompleter(self.sn_autocomplete_list),
            QCompleter(self.particulars_autocomplete_list),
            QCompleter(self.hsn_code_autocomplete_list),
            QCompleter(self.qty_autocomplete_list),
            QCompleter(self.uom_autocomplete_list),
            QCompleter(self.price_autocomplete_list),
            QCompleter(self.igst_autocomplete_list)
        ]

        for completer in column_completers:
            completer.setCaseSensitivity(Qt.CaseInsensitive)

        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                item = QTableWidgetItem()
                self.table.setItem(row, column, item)
                line_edit = QLineEdit()
                line_edit.setCompleter(column_completers[column])
                self.table.setCellWidget(row, column, line_edit)

    def setup_autocomplete(self, line_edit, suggestions):
        completer = QCompleter(suggestions)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        line_edit.setCompleter(completer)

    def create_footer_section(self):
        self.total_input = QLineEdit()


        self.setup_autocomplete(self.total_input, self.freight_charges_autocomplete_list)

        footer_frame = QFrame()
        footer_layout = QVBoxLayout()

        footer_layout.addWidget(QLabel("FREIGHT CHARGES"))
        footer_layout.addWidget(self.total_input)

        footer_frame.setLayout(footer_layout)
        return footer_frame

    def clear_inputs(self):
        self.invoice_input.clear()
        self.date_input.clear()
        self.po_input.clear()
        self.contact_input.clear()
        self.billed_to_line_edit.clear()
        self.billed_to_gstin_line_edit.clear()
        self.shipped_to_line_edit.clear()
        self.shipped_to_gstin_line_edit.clear()
        self.total_input.clear()

        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                widget = self.table.cellWidget(row, column)
                if widget:
                    widget.clear()

        self.date_input.setText(datetime.today().strftime('%d/%m/%Y'))

    def generate_form(self):
        self.data_dict = {
            "invoice_no": self.invoice_input.text(),
            "date": self.date_input.text(),
            "buyers_po_no": self.po_input.text(),
            "contact_person": self.contact_input.text(),
            "billed_to": self.billed_to_line_edit.text(),
            "billed_to_gstin": self.billed_to_gstin_line_edit.text(),
            "shipped_to": self.shipped_to_line_edit.text(),
            "shipped_to_gstin": self.shipped_to_gstin_line_edit.text(),
            "freight_charges": self.total_input.text(),
            "table_data": []
        }

        for row in range(self.table.rowCount()):
            row_data = []
            for column in range(self.table.columnCount()):
                widget = self.table.cellWidget(row, column)
                row_data.append(widget.text() if widget else "")
            self.data_dict["table_data"].append(row_data)
        
        copy_data_dict = copy.deepcopy(self.data_dict)
        
        formatted_data = self.format_data(copy_data_dict)
        self.write_data_to_json(formatted_data[0], formatted_data[1])
        self.get_json_data()
        self.refresh_autocomplete()
        
        
        table_data = self.data_dict['table_data']
        self.data_dict.pop('table_data')
                
        print(self.data_dict)
        
        pi_no = self.data_dict['invoice_no']

        if self.data_dict['freight_charges'] != '':
            try:
                freight_charges = float(self.data_dict['freight_charges'])
            except:
                return
        else:
            freight_charges = 0
        
        for key, value in self.data_dict.items():
            if key in ['billed_to', 'shipped_to'] and value!='':
                new_list = format_text(value, 25)
                coords = COORDINATES[key]
                for n, sentence in enumerate(new_list):
                    self.pdfmaker.draw(sentence, coords['x'], coords['y']-n*COORDINATES['LINE_GAP_ADDRESS'], coords['font'], coords['color'], coords['size'])
                
            elif key!='freight_charges' and value != '':
                coords = COORDINATES[key]
                self.pdfmaker.draw(value, coords['x'], coords['y'], coords['font'], coords['color'], coords['size'])

        headers = ["sno", "particulars", "hsn", "qty", "uom", "price", "igst%"]
        
        tax_percent_in_each_row = []
        amounts_before_taxes = []
        taxes_in_each_row = []
        
        for n, lst in enumerate(table_data):
            for m, item in enumerate(lst):
                if item != '':
                    key = headers[m]
                    coords = COORDINATES[key]
                    self.pdfmaker.draw(item, coords['x'], (coords['y']-(COORDINATES["LINE_GAP_MAIN_Y"]*n)), coords['font'], coords['color'], coords['size'])

                    if m == 6:
                        tax_percent_in_each_row.append(float(item))
            
            if lst[3] != '' and lst[5] != '':
                try:
                    amount_before_tax = float(lst[3])*float(lst[5])
                    coords = COORDINATES["amount_before_tax"]
                    self.pdfmaker.draw(str(amount_before_tax), coords['x'], (coords['y']-(COORDINATES["LINE_GAP_MAIN_Y"]*n)), coords['font'], coords['color'], coords['size'])

                    amounts_before_taxes.append(amount_before_tax)
                    
                except Exception as e:
                    return None

        total_amount_before_tax = 0
        for i in amounts_before_taxes:
            total_amount_before_tax+=i
        
        for n, i in enumerate(amounts_before_taxes):
            taxes_in_each_row.append(tax_percent_in_each_row[n]*i/100)
        
        total_tax = 0
        for i in taxes_in_each_row:
            total_tax += i
        
        coords = COORDINATES["total_amount_before_tax"]
        self.pdfmaker.draw(str(total_amount_before_tax), coords['x'], coords['y'], coords['font'], coords['color'], coords['size'])
        
        coords = COORDINATES["total_tax"]
        self.pdfmaker.draw(str(round(total_tax, 2)), coords['x'], coords['y'], coords['font'], coords['color'], coords['size'])
        
        try:
            freight_tax = max(tax_percent_in_each_row)
        except:
            freight_tax = 0

        total_freight_charges = freight_charges + freight_tax*freight_charges/100

        grand_total = total_amount_before_tax+total_tax+total_freight_charges 
        
        rounded_off_grand_total = round(grand_total)

        round_off = round(rounded_off_grand_total - grand_total, 2)
        
        coords = COORDINATES["grand_total"]
        self.pdfmaker.draw(str(rounded_off_grand_total), coords['x'], coords['y'], coords['font'], coords['color'], coords['size'])
        
        coords = COORDINATES["round_off"]
        self.pdfmaker.draw(str(round_off), coords['x'], coords['y'], coords['font'], coords['color'], coords['size'])

        if freight_charges != 0:
            coords = COORDINATES["freight_charges"]
            self.pdfmaker.draw(str(total_freight_charges), coords['x'], coords['y'], coords['font'], coords['color'], coords['size'])

            coords = COORDINATES["freight_disclaimer"]
            self.pdfmaker.draw(f"(inluding IGST@{freight_tax}%)", coords['x'], coords['y'], coords['font'], coords['color'], coords['size'])


        self.pdfmaker.render_pdf(f"invoice_{pi_no}")
        self.pdfmaker.refresh()
    
        # AUTO DATE
        
    def format_data(self, data):
        data.pop("invoice_no")
        del data["date"]
        data.pop("freight_charges")
        
        table_data = data["table_data"]
        
        del data["table_data"]
        
        indexes = []
        
        for n, lst in enumerate(table_data):
            to_del = True
            for elem in lst:
                if elem != '':
                    to_del = False
                    break
            if not to_del:
                indexes.append(n)
                        
        
        final_table_data = []
        
        for i in indexes:
            table_data[i].pop(0)
            table_data[i].pop(2)
            final_table_data.append(table_data[i])

        return data, final_table_data
        
    def write_data_to_json(self, data, final_table_data):
        
        
        with open('db.json', 'r') as file:
            existing_data = json.load(file)
            
        values_to_be_added = []

        for key, value in data.items():
            if value != '':
                if value not in existing_data[key]:
                    values_to_be_added.append((key, value))
        
        headers = ["particulars", "hsn", "uom", "price", "igst%"]
        
        for lst in final_table_data:
            for n, item in enumerate(lst):
                if item != '':
                    if item not in existing_data[headers[n]]:
                        values_to_be_added.append((headers[n], item))
        
        for i in values_to_be_added:
            existing_data[i[0]].append(i[1])
            
        with open('db.json', 'w') as file:
            json.dump(existing_data, file)
        
    def get_json_data(self):
        with open('db.json', 'r') as file:
            data = json.load(file)
            
        self.particulars_autocomplete_list = data['particulars']
        self.hsn_code_autocomplete_list = data['hsn']
        self.uom_autocomplete_list = data['uom']
        self.price_autocomplete_list = data['price']
        self.igst_autocomplete_list = data['igst%']
        self.po_autocomplete_list = data['buyers_po_no']
        self.contact_autocomplete_list = data['contact_person']
        self.billed_to_autocomplete_list = data['billed_to']
        self.billed_to_gstin_autocomplete_list = data['billed_to_gstin']
        self.shipped_to_autocomplete_list = data['shipped_to']
        self.shipped_to_gstin_autocomplete_list = data['shipped_to_gstin']
        
        
    def refresh_autocomplete(self):
        self.setup_table_autocomplete()
        
        self.setup_autocomplete(self.total_input, self.freight_charges_autocomplete_list)
        
        self.setup_autocomplete(self.invoice_input, self.invoice_autocomplete_list)
        self.setup_autocomplete(self.date_input, self.date_autocomplete_list)
        self.setup_autocomplete(self.po_input, self.po_autocomplete_list)
        self.setup_autocomplete(self.contact_input, self.contact_autocomplete_list)

        self.setup_autocomplete(self.billed_to_line_edit, self.billed_to_autocomplete_list)
        self.setup_autocomplete(self.billed_to_gstin_line_edit, self.billed_to_gstin_autocomplete_list)
        self.setup_autocomplete(self.shipped_to_line_edit, self.shipped_to_autocomplete_list)
        self.setup_autocomplete(self.shipped_to_gstin_line_edit, self.shipped_to_gstin_autocomplete_list)




class PdfMaker:
    def __init__(self):

        self.packet = io.BytesIO()
        self.can = canvas.Canvas(self.packet, pagesize=A4)

        try:
            pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial_Bold', 'Arial_Bold.ttf'))

        except:
            pass
            

    def draw(self, text, x, y, font, color, size):
        self.can.setFont(font, size)
        self.can.setFillColor(color)

        self.can.drawString(x, y, text) 


    def render_pdf(self, filename):
        self.can.save()
        self.packet.seek(0)
        
        new_pdf = PdfReader(self.packet)
        
        existing_pdf = PdfWriter(open("base_pdf.pdf", "rb"))
        
        output = PdfWriter(self.packet)

        page = existing_pdf.pages[0]

        page.merge_page(new_pdf.pages[0])

        output.add_page(page)
        page0 = output.pages[0]
        output.remove_page(page0)

        desktop_path = os.path.expanduser("~/Desktop")

        if 'PIs' not in os.listdir(desktop_path):
            os.mkdir(f"{desktop_path}/PIs")

        save_path = f"{desktop_path}/PIs/{filename}.pdf"

        output_stream = open(save_path, "wb")

        output.write(output_stream)

        output_stream.close()
        
    def refresh(self):
        self.packet = io.BytesIO()
        self.can = canvas.Canvas(self.packet, pagesize=A4)


try:
    f = open('db.json', 'r')
    f.close()
    del f
    
except FileNotFoundError:
    with open('db.json', 'w') as f:
        f.write('''
{
    "billed_to": [
        
    ],

    "shipped_to": [

    ],

    "buyers_po_no": [
        
    ],

    "particulars": [
    
    ],

    "hsn": [

    ],

    "uom": [

    ],

    "price": [

    ],

    "igst%": [

    ],

    "contact_person": [

    ],

    "billed_to_gstin": [

    ],

    "shipped_to_gstin": [

    ]

}
''')
    
app = QApplication(sys.argv)
form = InvoiceForm()
form.show()

sys.exit(app.exec_())


