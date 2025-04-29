from flask import Flask, render_template, request, redirect, url_for
import os
from utils.pdf_reader import parse_invoice_from_pdf
from database import Session
from models import Invoice
from datetime import datetime


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Upewnij się, że folder uploads istnieje!
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Strona główna
@app.route('/')
def home():
    return render_template('home.html')

# Dodawanie rozliczenia dnia
@app.route('/add-daily', methods=['GET', 'POST'])
def add_daily():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        print(form_data)
        return redirect(url_for('home'))
    return render_template('add_daily.html')

# Dodawanie faktury ręcznie
@app.route('/add-invoice', methods=['GET', 'POST'])
def add_invoice():
    if request.method == 'POST':
        form_data = request.form.to_dict()

        invoice_date_str = form_data.get('purchase_date')
        invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d").date() if invoice_date_str else None

        session = Session()
        invoice = Invoice(
            filename=form_data.get('filename', 'manual-entry'),
            invoice_date=invoice_date,
            gross_amount=float(form_data['gross_amount']),
            net_amount=float(form_data.get('net_amount', 0)),
            supplier_nip=form_data.get('supplier_nip', ''),
            supplier_name=form_data.get('supplier', ''),
            category=form_data['category']
        )
        session.add(invoice)
        session.commit()

        # Zapisz ID dodanej faktury
        new_invoice_id = invoice.id

        session.close()

        # Przekieruj do nowej strony
        return redirect(url_for('invoice_saved', invoice_id=new_invoice_id))

    return render_template('add_invoice.html', dane={})


# Upload pliku PDF i automatyczne wypełnienie
@app.route('/upload-invoice', methods=['POST'])
def upload_invoice():
    if 'pdf_file' not in request.files:
        print("❌ Brak pdf_file w request.files")
        return redirect(url_for('add_invoice'))

    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        print("❌ Plik bez nazwy")
        return redirect(url_for('add_invoice'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
    pdf_file.save(file_path)
    print(f"✅ Plik zapisany: {file_path}")

    dane = parse_invoice_from_pdf(file_path)
    if not dane:
        print("⚠️ Parser zwrócił None albo pusty słownik!")
        dane = {}
    else:
        print("✅ Dane sparsowane z faktury:", dane)

    return render_template('add_invoice.html', dane=dane)

#nowa trasa- zapisane faktury
@app.route('/invoice-saved/<int:invoice_id>')
def invoice_saved(invoice_id):
    session = Session()
    invoice = session.query(Invoice).get(invoice_id)
    session.close()

    if invoice:
        return render_template('invoice_saved.html', invoice=invoice)
    else:
        return "Nie znaleziono faktury", 404



@app.route('/daily-summary')
def daily_summary():
    return "Strona Podsumowania dziennego - jeszcze w budowie."

@app.route('/weekly-summary')
def weekly_summary():
    return "Strona Podsumowania tygodniowego - jeszcze w budowie."

@app.route('/monthly-summary')
def monthly_summary():
    return "Strona Podsumowania miesięcznego - jeszcze w budowie."


#ŚCIEZKA TESTOWA- DO USUNIĘCIA
@app.route('/test-invoices')
def test_invoices():
    session = Session()
    invoices = session.query(Invoice).all()
    session.close()

    output = "<h2>Zapisane faktury:</h2><ul>"
    for inv in invoices:
        output += f"<li>{inv.invoice_date} – {inv.supplier_name} – {inv.gross_amount} zł – {inv.category}</li>"
    output += "</ul>"

    return output

if __name__ == '__main__':
    app.run(debug=True)
