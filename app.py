from flask import Flask, render_template, request, redirect, url_for
import os
from utils.pdf_reader import parse_invoice_from_pdf
from database import Session
from models import Revenue, Invoice
from datetime import datetime, date
from sqlalchemy import func
from collections import defaultdict

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

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

#EDYCJA I USUWANIE FAKTUR
@app.route('/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    invoice = Session().query(Invoice).get(invoice_id)
    if request.method == 'POST':
        invoice.invoice_date = request.form['invoice_date']
        invoice.gross_amount = float(request.form['gross_amount'])
        invoice.supplier_name = request.form['supplier_name']
        invoice.supplier_nip = request.form['supplier_nip']
        invoice.category = request.form['category']
        Session().commit()
        return redirect(url_for('dashboard'))
    return render_template('edit_invoice.html', invoice=invoice)

@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    session = Session()
    invoice = session.query(Invoice).get(invoice_id)
    session.delete(invoice)
    session.commit()
    return redirect(url_for('dashboard'))


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
        return ("Nie znaleziono faktury", 404)

@app.route('/monthly-summary')
def monthly_summary():
    start_date = date(2025, 4, 1)
    end_date = date(2025, 4, 30)

    session = Session()

    # Faktury z danego miesiąca
    invoices = session.query(Invoice).filter(
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date
    ).all()

    # Tymczasowe wartości podsumowania – tu wrzuć swój prawdziwy kod
    summary = {
        "total_revenue": 0,
        "total_costs": 0,
        "net_result": 0,
        "cost_by_category": {}
    }

    return render_template(
        "monthly_summary.html",
        summary=summary,
        invoices=invoices
    )

    # 1. Utargi
    revenues = session.query(
        Revenue.revenue_type,
        func.sum(Revenue.amount)
    ).filter(
        Revenue.revenue_date >= start_date,
        Revenue.revenue_date <= end_date
    ).group_by(Revenue.revenue_type).all()

    total_revenue = sum(amount for _, amount in revenues)

    # 2. Koszty
    invoices = session.query(
        Invoice.category,
        func.sum(Invoice.gross_amount)
    ).filter(
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date
    ).group_by(Invoice.category).all()

    total_costs = sum(amount for _, amount in invoices)

    # 3. Dane do wykresu
    cost_by_category = {cat: float(amount) for cat, amount in invoices}

    session.close()

    # 4. Dane do szablonu
    summary = {
        'revenues': revenues,
        'total_revenue': total_revenue,
        'costs': invoices,
        'total_costs': total_costs,
        'net_result': total_revenue - total_costs,
        'cost_by_category': cost_by_category
    }

    return render_template('monthly_summary.html', summary=summary)



@app.route('/daily-summary')
def daily_summary():
    return "Strona Podsumowania dziennego - jeszcze w budowie."

@app.route('/weekly-summary')
def weekly_summary():
    return "Strona Podsumowania tygodniowego - jeszcze w budowie."



#TESTY- DO USUNIĘCIA
@app.route('/test-invoices')
def test_invoices():
    session = Session()
    invoices = session.query(Invoice).all()
    session.close()

    output = "<h2>Faktury w bazie</h2><ul>"
    for inv in invoices:
        output += f"<li>{inv.invoice_date} | {inv.supplier_name} | {inv.gross_amount} zł</li>"
    output += "</ul>"

    return output


if __name__ == '__main__':
    app.run(debug=True)
