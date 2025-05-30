# SKRÓCONY POCZĄTEK – BEZ ZMIAN
from flask import Flask, render_template, request, session, redirect, url_for
from utils.pdf_reader import parse_invoice_from_pdf
from database import Session
from models import Revenue, Invoice, RozliczenieDzien
import datetime
from sqlalchemy import func
from collections import defaultdict
import os
import json
from utils.nip_utils import get_category_for_nip, save_category_for_nip

with open('utils/data/config.json') as f:
    config = json.load(f)

app = Flask(__name__)
app.secret_key = "Sbc3394left!"
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/add-invoice', methods=['GET', 'POST'])
def add_invoice():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        invoice_date_str = form_data.get('purchase_date')
        invoice_date = datetime.datetime.strptime(invoice_date_str, "%Y-%m-%d").date() if invoice_date_str else None

        db_session = Session()
        invoice = Invoice(
            filename=form_data.get('filename', 'manual-entry'),
            invoice_date=invoice_date,
            gross_amount=float(form_data['gross_amount']),
            net_amount=float(form_data.get('net_amount', 0)),
            nip=form_data.get('supplier_nip', ''),
            supplier=form_data.get('supplier', ''),
            category=form_data['category'],
            lokal=session['lokal']
        )
        db_session.add(invoice)
        db_session.commit()

        if invoice.nip and invoice.category:
            save_category_for_nip(invoice.nip, invoice.category)

        new_invoice_id = invoice.id
        db_session.close()
        return redirect(url_for('invoice_saved', invoice_id=new_invoice_id))

    return render_template('add_invoice.html', dane={})

@app.route('/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    db_session = Session()
    invoice = db_session.query(Invoice).get(invoice_id)

    if request.method == 'POST':
        invoice.invoice_date = datetime.datetime.strptime(request.form['invoice_date'], "%Y-%m-%d").date()
        invoice.gross_amount = float(request.form['gross_amount'])
        invoice.supplier = request.form['supplier_name']
        invoice.nip = request.form['supplier_nip']
        invoice.category = request.form['category']
        invoice.net_amount = float(request.form.get('net_amount', 0))
        db_session.commit()
        db_session.close()
        return redirect(url_for('monthly_summary'))

    db_session.close()
    return render_template('edit_invoice.html', invoice=invoice)

@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    db_session = Session()
    invoice = db_session.query(Invoice).get(invoice_id)
    db_session.delete(invoice)
    db_session.commit()
    return redirect(url_for('monthly_summary'))

@app.route('/upload-invoice', methods=['POST'])
def upload_invoice():
    if 'pdf_file' not in request.files:
        return redirect(url_for('add_invoice'))

    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return redirect(url_for('add_invoice'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
    pdf_file.save(file_path)

    dane = parse_invoice_from_pdf(file_path)
    if not dane:
        dane = {}

    nip = dane.get("nip")
    if nip:
        kat = get_category_for_nip(nip)
        if kat:
            dane["category"] = kat

    dane["gross_amount"] = dane.get("kwota brutto", "")
    dane["net_amount"] = dane.get("kwota netto", "")
    dane["filename"] = pdf_file.filename

    return render_template('add_invoice.html', dane=dane)

@app.route('/invoice-saved/<int:invoice_id>')
def invoice_saved(invoice_id):
    db_session = Session()
    invoice = db_session.query(Invoice).get(invoice_id)
    db_session.close()

    if invoice:
        return render_template('invoice_saved.html', invoice=invoice)
    else:
        return ("Nie znaleziono faktury", 404)

@app.route('/add_daily', methods=['GET', 'POST'])
def add_daily():
    # 🔹 Załaduj aktualne ustawienia checkboxów
    with open('utils/data/config.json') as f:
        config = json.load(f)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'save_defaults':
            # 🔧 Zapisz domyślne ustawienia checkboxów
            przychody = []
            koszty = []

            for field in ['bar', 'kuchnia', 'wejsciowki', 'inne']:
                if request.form.get(f"sprzedaz_{field}") == 'on':
                    przychody.append(field)

            for field in ['bar', 'kelnerzy', 'kuchnia', 'ochrona', 'marketing', 'inne']:
                if request.form.get(f"koszt_{field}") == 'on':
                    koszty.append(field)

            new_config = {
                "domyslne_przychody": przychody,
                "domyslne_koszty": koszty
            }

            with open('utils/data/config.json', 'w') as f:
                json.dump(new_config, f, indent=4)

            return redirect(url_for('add_daily'))

        elif action == 'save_daily':
            db_session = Session()

            data_str = request.form.get('data')
            if not data_str:
                return "Brak daty – nie można zapisać rozliczenia", 400

            daily_date = datetime.datetime.strptime(data_str, '%Y-%m-%d').date()

            # 🔄 Sprawdź, czy taki dzień już istnieje
            existing = db_session.query(RozliczenieDzien).filter_by(daily_date=daily_date).first()
            if existing:
                db_session.close()
                return render_template('daily_exists.html', data=data_str)

            # 📦 Stwórz nowe rozliczenie
            roz = RozliczenieDzien(daily_date=daily_date)

            def get_kwota(field):
                val = request.form.get(f"kwota_{field}")
                try:
                    return float(val) if val else 0.0
                except ValueError:
                    return 0.0

            # Przychody
            roz.revenue_bar = get_kwota('sprzedaz_bar')
            roz.revenue_kitchen = get_kwota('sprzedaz_kuchnia')
            roz.revenue_entry = get_kwota('sprzedaz_wejsciowki')
            roz.revenue_other = get_kwota('sprzedaz_inne')
            roz.revenue_other_comment = request.form.get('sprzedaz_inne_komentarz')

            # Koszty
            roz.cost_bar = get_kwota('koszt_bar')
            roz.cost_waiters = get_kwota('koszt_kelnerzy')
            roz.cost_kitchen = get_kwota('koszt_kuchnia')
            roz.cost_marketing = get_kwota('koszt_marketing')
            roz.cost_marketing_comment = request.form.get('koszt_marketing_komentarz')
            roz.cost_security = get_kwota('koszt_ochrona')
            roz.cost_other = get_kwota('koszt_inne')
            roz.cost_other_comment = request.form.get('koszt_inne_komentarz')

            db_session.add(roz)
            db_session.commit()
            db_session.close()

            return redirect(url_for('daily_summary', data=data_str))

    # 🔹 Jeśli GET – pokaż formularz
    return render_template('add_daily.html', config=config)


@app.route('/daily-added')
def daily_added():
    return render_template('daily_added.html')

@app.route('/daily-summary', methods=['GET'])
def daily_summary():
    db_session = Session()

    # Pobierz wybrany miesiąc i rok z formularza lub ustaw domyślnie na dziś
    selected_month = int(request.args.get('month', datetime.date.today().month))
    selected_year = int(request.args.get('year', datetime.date.today().year))

    # Wylicz liczbę dni w miesiącu
    first_day = datetime.date(selected_year, selected_month, 1)
    if selected_month == 12:
        last_day = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)

    wszystkie_daty = [first_day + datetime.timedelta(days=i) for i in range((last_day - first_day).days + 1)]

    # Pobierz daty, które mają rozliczenie w bazie
    roz_dni = db_session.query(RozliczenieDzien.daily_date).filter(
        RozliczenieDzien.daily_date.between(first_day, last_day),
        RozliczenieDzien.lokal == session['lokal']
    ).all()
    roz_dni_set = {r[0] for r in roz_dni}

    # Stwórz listę dni z informacją ✔/✘
    dni_miesiaca = [{
        'data': d,
        'status': '✔' if d in roz_dni_set else '✘'
    } for d in wszystkie_daty]

    db_session.close()

    return render_template(
        'daily_summary.html',
        selected_month=selected_month,
        selected_year=selected_year,
        dni_miesiaca=dni_miesiaca
    )

@app.route('/monthly-summary')
def monthly_summary():
    selected_year = int(request.args.get('year', 2025))
    selected_month = int(request.args.get('month', 4))

    start_date = datetime.date(selected_year, selected_month, 1)
    if selected_month == 12:
        end_date = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)

    db_session = Session()

    # --- PRZYCHODY z rozliczeń dziennych
    rozliczenia = db_session.query(RozliczenieDzien).filter(
        RozliczenieDzien.daily_date >= start_date,
        RozliczenieDzien.daily_date <= end_date,
        RozliczenieDzien.lokal == session['lokal']
    ).all()

    total_revenue = sum([
        (r.revenue_bar or 0) +
        (r.revenue_kitchen or 0) +
        (r.revenue_entry or 0) +
        (r.revenue_other or 0)
        for r in rozliczenia
    ])

    # --- KOSZTY z rozliczeń dziennych
    total_costs_dzien = sum([
        (r.cost_bar or 0) +
        (r.cost_waiters or 0) +
        (r.cost_kitchen or 0) +
        (r.cost_marketing or 0) +
        (r.cost_security or 0) +
        (r.cost_other or 0)
        for r in rozliczenia
    ])

    # --- KOSZTY z faktur
    total_costs_faktury = db_session.query(func.sum(Invoice.gross_amount)).filter(
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date,
        Invoice.lokal == session['lokal']
    ).scalar() or 0

    # --- SUMA całkowita kosztów
    total_costs = total_costs_dzien + total_costs_faktury

    # --- Koszty według kategorii (na razie tylko z rozliczeń dziennych)
    cost_by_category = {
        'obsługa baru': sum(r.cost_bar or 0 for r in rozliczenia),
        'obsługa kelnerska': sum(r.cost_waiters or 0 for r in rozliczenia),
        'obsługa kuchni': sum(r.cost_kitchen or 0 for r in rozliczenia),
        'marketing': sum(r.cost_marketing or 0 for r in rozliczenia),
        'ochrona': sum(r.cost_security or 0 for r in rozliczenia),
        'inne': sum(r.cost_other or 0 for r in rozliczenia),
        'faktury': total_costs_faktury
    }

    # --- Faktury (do tabeli)
    invoices = db_session.query(Invoice).filter(
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date,
        Invoice.lokal == session['lokal']
    ).all()

    db_session.close()

    summary = {
        'total_revenue': total_revenue,
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

@app.route('/summary/period', methods=['GET'])
def summary_period():
    mode = request.args.get("mode")
    db_session = Session()
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
        year = request.args.get("year")
        month = request.args.get("month")
        if year and month:
            try:
                start = datetime.datetime.strptime(f"{year}-{month}", "%Y-%m").date()
                next_month = (start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
                end = next_month - datetime.timedelta(days=1)
                label = f"{start.strftime('%B')} {year}"
                date_range = [start, end]
            except ValueError:
                label = "Niepoprawna data"


    elif mode == "custom":
        start_str = request.args.get("start_date")
        end_str = request.args.get("end_date")
        if start_str and end_str:
            start = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
            label = f"{start} – {end}"
            date_range = [start, end]

    if date_range:
        entries = db_session.query(RozliczenieDzien).filter(
            RozliczenieDzien.daily_date >= date_range[0],
            RozliczenieDzien.daily_date <= date_range[1],
            RozliczenieDzien.lokal == session['lokal']
        ).all()

        income_breakdown = {
            "Bar": sum(e.revenue_bar or 0 for e in entries),
            "Kuchnia": sum(e.revenue_kitchen or 0 for e in entries),
            "Wejściówki": sum(e.revenue_entry or 0 for e in entries),
            "Inne": sum(e.revenue_other or 0 for e in entries),
        }
        total_income = sum(income_breakdown.values())

        expense_breakdown = {
            "Obsługa baru": sum(e.cost_bar or 0 for e in entries),
            "Obsługa kelnerska": sum(e.cost_waiters or 0 for e in entries),
            "Obsługa kuchni": sum(e.cost_kitchen or 0 for e in entries),
            "Marketing": sum(e.cost_marketing or 0 for e in entries),
            "Ochrona": sum(e.cost_security or 0 for e in entries),
            "Inne": sum(e.cost_other or 0 for e in entries),
        }
        total_expenses = sum(expense_breakdown.values())
        result = total_income - total_expenses

        return render_template(
            "summary_period.html",
            summary={
                "range": label,
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "result": round(result, 2),
                "income_breakdown": income_breakdown,
                "expense_breakdown": expense_breakdown
            },
            now=datetime.datetime.now()
        )

    return render_template("summary_period.html", summary=None, now=datetime.datetime.now())


@app.route('/edit-daily/<data>', methods=['GET', 'POST'])
def edit_daily(data):
    db_session = Session()
    data_obj = datetime.datetime.strptime(data, '%Y-%m-%d').date()
    roz = db_session.query(RozliczenieDzien).filter_by(daily_date=data_obj).first()

    if request.method == 'POST':
        def get_kwota(field):
            return float(request.form.get(f"{field}_kwota", 0)) if request.form.get(field) else 0

        roz.revenue_bar = get_kwota('sprzedaz_bar')
        roz.revenue_kitchen = get_kwota('sprzedaz_kuchnia')
        roz.revenue_entry = get_kwota('sprzedaz_wejsciowki')
        roz.revenue_other = get_kwota('sprzedaz_inne')

        roz.cost_bar = get_kwota('koszt_bar')
        roz.cost_waiters = get_kwota('koszt_kelnerzy')
        roz.cost_kitchen = get_kwota('koszt_kuchnia')
        roz.cost_security = get_kwota('koszt_ochrona')
        roz.cost_marketing = get_kwota('koszt_marketing')
        roz.cost_marketing_comment = request.form.get('koszt_marketing_komentarz', '')
        roz.cost_other = get_kwota('koszt_inne')
        roz.cost_other_comment = request.form.get('koszt_inne_komentarz', '')

        db_session.commit()
        db_session.close()
        return redirect(url_for('daily_summary', data=data))

    # MAPOWANIE NA FORMAT HTML (czyli np. sprzedaz_bar zamiast revenue_bar)
    roz_dict = {
        'sprzedaz_bar': roz.revenue_bar,
        'sprzedaz_kuchnia': roz.revenue_kitchen,
        'sprzedaz_wejsciowki': roz.revenue_entry,
        'sprzedaz_inne': roz.revenue_other,
        'koszt_bar': roz.cost_bar,
        'koszt_kelnerzy': roz.cost_waiters,
        'koszt_kuchnia': roz.cost_kitchen,
        'koszt_ochrona': roz.cost_security,
        'koszt_marketing': roz.cost_marketing,
        'koszt_marketing_komentarz': roz.cost_marketing_comment,
        'koszt_inne': roz.cost_other,
        'koszt_inne_komentarz': roz.cost_other_comment,
    }

    db_session.close()
    return render_template('edit_daily.html', roz=roz_dict, data=data)

@app.route('/delete_daily/<data>', methods=['POST'])
def delete_daily(data):
    db_session = Session()
    lokal = session.get("lokal")  # jeśli rozliczenia są przypisane do lokalu
    data_obj = datetime.datetime.strptime(data, '%Y-%m-%d').date()

    roz = db_session.query(RozliczenieDzien).filter_by(daily_date=data_obj, lokal=lokal).first()
    if roz:
        db_session.delete(roz)
        db_session.commit()

    db_session.close()
    return redirect(url_for('daily_summary'))

@app.route('/sync-revenue')
def sync_revenue():
    db_session = Session()
    rozliczenia = db_session.query(RozliczenieDzien).all()
    dodano = 0

    for r in rozliczenia:
        suma = sum([
            r.revenue_bar or 0,
            r.revenue_kitchen or 0,
            r.revenue_entry or 0,
            r.revenue_other or 0
        ])
        if suma > 0:
            db_session.add(Revenue(
                revenue_date=r.daily_date,
                amount=suma,
                revenue_type='Z dziennych rozliczeń',
                lokal=r.lokal
            ))
            dodano += 1

    db_session.commit()
    db_session.close()
    return f"✅ Zsynchronizowano {dodano} rekordów do tabeli Revenue."


@app.route('/set-lokal', methods=['POST'])
def set_lokal():
    session['lokal'] = request.form['lokal']
    return redirect(request.referrer or url_for('index'))


@app.before_request
def set_default_lokal():
    if 'lokal' not in session:
        session['lokal'] = 'Rokoko 2.0'

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

    print("NOWE USTAWIENIA:")
    print(new_config)

    return redirect(url_for('add_daily'))


if __name__ == '__main__':
    app.run(debug=True)
