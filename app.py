from flask import Flask, render_template, request, redirect, url_for
from utils.pdf_reader import parse_invoice_from_pdf
from database import Session
from models import Revenue, Invoice, RozliczenieDzien
import datetime
from sqlalchemy import func
from collections import defaultdict
import os
import json

with open('utils/data/config.json') as f:
    config = json.load(f)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Strona główna
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/add-invoice', methods=['GET', 'POST'])
def add_invoice():
    import datetime

    if request.method == 'POST':
        form_data = request.form.to_dict()

        invoice_date_str = form_data.get('purchase_date')
        invoice_date = datetime.datetime.strptime(invoice_date_str, "%Y-%m-%d").date() if invoice_date_str else None

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

        new_invoice_id = invoice.id
        session.close()

        return redirect(url_for('invoice_saved', invoice_id=new_invoice_id))

    # 👇 TEN RETURN DODAJ lub popraw
    return render_template('add_invoice.html', dane={})


@app.route('/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    import datetime
    session = Session()
    invoice = session.query(Invoice).get(invoice_id)

    if request.method == 'POST':
        invoice.invoice_date = datetime.datetime.strptime(request.form['invoice_date'], "%Y-%m-%d").date()
        invoice.gross_amount = float(request.form['gross_amount'])
        invoice.supplier_name = request.form['supplier_name']
        invoice.supplier_nip = request.form['supplier_nip']
        invoice.category = request.form['category']
        session.commit()
        session.close()
        return redirect(url_for('dashboard'))

    session.close()
    return render_template('edit_invoice.html', invoice=invoice)


@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    session = Session()
    invoice = session.query(Invoice).get(invoice_id)
    session.delete(invoice)
    session.commit()
    return redirect(url_for('dashboard'))


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

    print("✅ Dane sparsowane z faktury:", dane)

    # 🔁 Mapujemy kwoty na klucze, których używa HTML
    dane["gross_amount"] = dane.get("kwota brutto", "")
    dane["net_amount"] = dane.get("kwota netto", "")

    # Dodajemy nazwę pliku
    dane["filename"] = pdf_file.filename

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

@app.route('/daily-summary', methods=['GET'])
def daily_summary():
    selected_date = request.args.get('data')
    rozliczenie = None
    wynik = None

    if selected_date:
        session = Session()
        data_obj = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()
        rozliczenie = session.query(RozliczenieDzien).filter_by(data=data_obj).first()
        session.close()

        if rozliczenie:
            przychody = sum([
                rozliczenie.sprzedaz_bar or 0,
                rozliczenie.sprzedaz_kuchnia or 0,
                rozliczenie.sprzedaz_wejsciowki or 0,
                rozliczenie.sprzedaz_inne or 0
            ])
            koszty = sum([
                rozliczenie.koszt_bar or 0,
                rozliczenie.koszt_kelnerzy or 0,
                rozliczenie.koszt_kuchnia or 0,
                rozliczenie.koszt_marketing or 0,
                rozliczenie.koszt_ochrona or 0,
                rozliczenie.koszt_inne or 0
            ])
            wynik = round(przychody - koszty, 2)

    return render_template(
        'daily_summary.html',
        selected_date=selected_date,
        rozliczenie=rozliczenie,
        wynik=wynik
    )

from flask import request  # dodaj na górze

@app.route('/monthly-summary')
def monthly_summary():
    import datetime  # Upewniamy się, że mamy pełny import

    selected_year = int(request.args.get('year', 2025))
    selected_month = int(request.args.get('month', 4))

    # Wylicz zakres dat na podstawie wybranego miesiąca
    start_date = datetime.date(selected_year, selected_month, 1)
    if selected_month == 12:
        end_date = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)

    session = Session()

    # 🔍 DEBUG (możesz usunąć później)
    print(f"▶️ Podsumowanie dla: {start_date} – {end_date}")

    # 1. Utargi
    revenues = session.query(
        Revenue.revenue_type,
        func.sum(Revenue.amount)
    ).filter(
        Revenue.revenue_date >= start_date,
        Revenue.revenue_date <= end_date
    ).group_by(Revenue.revenue_type).all()

    total_revenue = sum(amount for _, amount in revenues)

    # 2. Koszty – agregacja do wykresów
    costs_by_category = session.query(
        Invoice.category,
        func.sum(Invoice.gross_amount)
    ).filter(
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date
    ).group_by(Invoice.category).all()

    total_costs = sum(amount for _, amount in costs_by_category)
    cost_by_category = {cat: float(amount) for cat, amount in costs_by_category}

    # 3. Lista faktur do wyświetlenia w tabeli
    invoices = session.query(Invoice).filter(
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date
    ).all()

    session.close()

    # 4. Dane do szablonu
    summary = {
        'revenues': revenues,
        'total_revenue': total_revenue,
        'costs': costs_by_category,
        'total_costs': total_costs,
        'net_result': total_revenue - total_costs,
        'cost_by_category': cost_by_category
    }

    return render_template(
        'monthly_summary.html',
        summary=summary,
        invoices=invoices,
        selected_month=selected_month,
        selected_year=selected_year
    )




@app.route('/add_daily', methods=['GET', 'POST'])
def add_daily():
    if request.method == 'POST':
        session = Session()

        # Data
        data_str = request.form.get('data')
        data = datetime.datetime.strptime(data_str, '%Y-%m-%d').date()

        existing = session.query(RozliczenieDzien).filter_by(data=data).first()
        if existing:
            session.close()
            return render_template('daily_exists.html', data=data)

        # Przygotowanie słownika z danymi
        def get_kwota(field):
            if request.form.get(field):
                kwota = request.form.get(f"{field}_kwota")
                return float(kwota) if kwota else 0
            return 0

        roz = RozliczenieDzien(
            data=data,
            # Przychody
            sprzedaz_bar=get_kwota('sprzedaz_bar'),
            sprzedaz_kuchnia=get_kwota('sprzedaz_kuchnia'),
            sprzedaz_wejsciowki=get_kwota('sprzedaz_wejsciowki'),
            sprzedaz_inne=get_kwota('sprzedaz_inne'),

            # Koszty
            koszt_bar=get_kwota('koszt_bar'),
            koszt_kelnerzy=get_kwota('koszt_kelnerzy'),
            koszt_kuchnia=get_kwota('koszt_kuchnia'),
            koszt_ochrona=get_kwota('koszt_ochrona'),
            koszt_marketing=get_kwota('koszt_marketing'),
            koszt_marketing_komentarz=request.form.get('koszt_marketing_komentarz', ''),
            koszt_inne=get_kwota('koszt_inne'),
            koszt_inne_komentarz=request.form.get('koszt_inne_komentarz', ''),
        )

        session.add(roz)
        session.commit()
        session.close()

        return redirect(url_for('daily_added'))

    return render_template('add_daily.html', config=config)

@app.route('/weekly-summary')
def weekly_summary():
    return "Podsumowanie tygodniowe – jeszcze w budowie."

@app.route('/save-defaults', methods=['POST'])
def save_defaults():
    przychody = []
    koszty = []

    for field in ['bar', 'kuchnia', 'wejsciowki', 'inne']:
        if request.form.get(f"sprzedaz_{field}"):
            przychody.append(field)

    for field in ['bar', 'kelnerzy', 'kuchnia', 'ochrona']:
        if request.form.get(f"koszt_{field}"):
            koszty.append(field)

    if request.form.get("koszt_marketing"):
        koszty.append("marketing")
    if request.form.get("koszt_inne"):
        koszty.append("inne")

    new_config = {
        "domyslne_przychody": przychody,
        "domyslne_koszty": koszty
    }

    with open('utils/data/config.json', 'w') as f:
        json.dump(new_config, f, indent=4)

    return redirect(url_for('add_daily'))

@app.route('/daily-added')
def daily_added():
    return render_template('daily_added.html')

@app.route('/edit-daily/<data>', methods=['GET', 'POST'])
def edit_daily(data):
    session = Session()
    data_obj = datetime.datetime.strptime(data, '%Y-%m-%d').date()
    roz = session.query(RozliczenieDzien).filter_by(data=data_obj).first()

    if request.method == 'POST':
        def get_kwota(field):
            return float(request.form.get(f"{field}_kwota", 0)) if request.form.get(field) else 0

        roz.sprzedaz_bar = get_kwota('sprzedaz_bar')
        roz.sprzedaz_kuchnia = get_kwota('sprzedaz_kuchnia')
        roz.sprzedaz_wejsciowki = get_kwota('sprzedaz_wejsciowki')
        roz.sprzedaz_inne = get_kwota('sprzedaz_inne')

        roz.koszt_bar = get_kwota('koszt_bar')
        roz.koszt_kelnerzy = get_kwota('koszt_kelnerzy')
        roz.koszt_kuchnia = get_kwota('koszt_kuchnia')
        roz.koszt_ochrona = get_kwota('koszt_ochrona')
        roz.koszt_marketing = get_kwota('koszt_marketing')
        roz.koszt_marketing_komentarz = request.form.get('koszt_marketing_komentarz', '')
        roz.koszt_inne = get_kwota('koszt_inne')
        roz.koszt_inne_komentarz = request.form.get('koszt_inne_komentarz', '')

        session.commit()
        session.close()
        return redirect(url_for('daily_summary', data=data))

    session.close()
    roz_dict = {col.name: getattr(roz, col.name) for col in roz.__table__.columns}
    return render_template('edit_daily.html', roz=roz_dict, data=data)

@app.route("/summary/period", methods=["GET"])
def summary_period():
    mode = request.args.get("mode")
    session = Session()
    date_range = []
    label = ""

    if mode == "weekly":
        start_date = request.args.get("week_start")
        if start_date:
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end = start + datetime.timedelta(days=6)
            label = f"{start} – {end}"
            date_range = [start, end]

    elif mode == "monthly":
        month_str = request.args.get("month")
        if month_str:
            start = datetime.datetime.strptime(month_str, "%Y-%m").date()
            next_month = (start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            end = next_month - datetime.timedelta(days=1)
            label = f"{start.strftime('%B %Y')}"
            date_range = [start, end]

    elif mode == "custom":
        start_str = request.args.get("start_date")
        end_str = request.args.get("end_date")
        if start_str and end_str:
            start = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
            label = f"{start} – {end}"
            date_range = [start, end]

    if date_range:
        entries = session.query(RozliczenieDzien).filter(
            RozliczenieDzien.data >= date_range[0],
            RozliczenieDzien.data <= date_range[1]
        ).all()

        # Agregacja PRZYCHODÓW
        income_breakdown = {
            "Bar": sum(e.sprzedaz_bar or 0 for e in entries),
            "Kuchnia": sum(e.sprzedaz_kuchnia or 0 for e in entries),
            "Wejściówki": sum(e.sprzedaz_wejsciowki or 0 for e in entries),
            "Inne": sum(e.sprzedaz_inne or 0 for e in entries),
        }
        total_income = sum(income_breakdown.values())

        # Agregacja KOSZTÓW
        expense_breakdown = {
            "Obsługa baru": sum(e.koszt_bar or 0 for e in entries),
            "Obsługa kelnerska": sum(e.koszt_kelnerzy or 0 for e in entries),
            "Obsługa kuchni": sum(e.koszt_kuchnia or 0 for e in entries),
            "Marketing": sum(e.koszt_marketing or 0 for e in entries),
            "Ochrona": sum(e.koszt_ochrona or 0 for e in entries),
            "Inne": sum(e.koszt_inne or 0 for e in entries),
        }
        total_expenses = sum(expense_breakdown.values())
        result = total_income - total_expenses

        return render_template("summary_period.html", summary={
            "range": label,
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "result": round(result, 2),
            "income_breakdown": income_breakdown,
            "expense_breakdown": expense_breakdown
        })

    return render_template("summary_period.html", summary=None)

@app.route('/sync-revenue')
def sync_revenue():
    import datetime
    session = Session()

    rozliczenia = session.query(RozliczenieDzien).all()
    dodano = 0

    for r in rozliczenia:
        suma = sum([
            r.sprzedaz_bar or 0,
            r.sprzedaz_kuchnia or 0,
            r.sprzedaz_wejsciowki or 0,
            r.sprzedaz_inne or 0
        ])

        # Nie dodawaj, jeśli suma to 0
        if suma > 0:
            session.add(Revenue(
                revenue_date=r.data,
                amount=suma,
                revenue_type='Z dziennych rozliczeń'
            ))
            dodano += 1

    session.commit()
    session.close()

    return f"✅ Zsynchronizowano {dodano} rekordów do tabeli Revenue."

if __name__ == '__main__':
    app.run(debug=True)
