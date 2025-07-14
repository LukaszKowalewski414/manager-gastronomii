# SKRÓCONY POCZĄTEK – BEZ ZMIAN
from flask import Flask, render_template, request, session, redirect, url_for
from utils.pdf_reader import parse_invoice_from_pdf
from database import Session
from models import Revenue, Invoice, RozliczenieDzien
from datetime import date
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

def get_current_lokal():
    return session.get('lokal', 'Rokoko 2.0')


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
            invoice_date=invoice_date,
            gross_amount=float(form_data['gross_amount']),
            net_amount=float(form_data.get('net_amount', 0)),
            nip=form_data.get('supplier_nip', ''),
            supplier=form_data.get('supplier', ''),
            invoice_number=form_data.get('invoice_number', ''),
            description=form_data.get('description', ''),  # ⬅️ to było pominięte
            category=form_data['category'],
            goods_type=form_data.get("goods_type"),
            lokal=get_current_lokal(),
            note=form_data.get('note', '').strip()
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

    # 🛡️ Zabezpiecz pobieranie tylko faktur z aktualnego lokalu
    invoice = db_session.query(Invoice).filter_by(
        id=invoice_id,
        lokal=get_current_lokal()
    ).first()

    if not invoice:
        db_session.close()
        return "Brak dostępu lub faktura nie istnieje", 404

    if request.method == 'POST':
        invoice.invoice_date = datetime.datetime.strptime(request.form['invoice_date'], "%Y-%m-%d").date()
        invoice.gross_amount = float(request.form['gross_amount'])
        invoice.supplier = request.form['supplier_name']
        invoice.nip = request.form['supplier_nip']
        invoice.category = request.form['category']
        invoice.goods_type = request.form.get("goods_type")
        invoice.net_amount = float(request.form.get('net_amount', 0))
        invoice.note = request.form.get('note', '').strip()

        db_session.commit()
        db_session.close()
        return redirect(url_for('monthly_summary'))

    db_session.close()
    return render_template('edit_invoice.html', invoice=invoice)

@app.route('/invoice/<int:invoice_id>')
def view_invoice(invoice_id):
    db_session = Session()
    invoice = db_session.query(Invoice).get(invoice_id)
    db_session.close()

    if not invoice:
        return "Faktura nie istnieje", 404

    return render_template("view_invoice.html", invoice=invoice)


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



    # 🔹 Jeśli GET – pokaż formularz
    return render_template('add_daily.html', config=config)

@app.route('/add_daily', methods=['GET', 'POST'])
def add_daily():
    default_date = request.args.get('data') or datetime.date.today().strftime('%Y-%m-%d')
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
            existing = db_session.query(RozliczenieDzien).filter_by(
                daily_date=daily_date,
                lokal=get_current_lokal()
            ).first()

            if existing:
                db_session.close()
                return render_template('daily_exists.html', data=data_str)

            # 📦 Stwórz nowe rozliczenie
            roz = RozliczenieDzien(
                daily_date=daily_date,
                lokal=get_current_lokal()
            )

            def get_kwota(field):
                val = request.form.get(f"kwota_{field}")
                try:
                    return float(val) if val else 0.0
                except ValueError:
                    return 0.0

            def get_int(field):
                val = request.form.get(field)
                try:
                    return int(val) if val else None
                except ValueError:
                    return None

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

            # Liczba pracowników
            roz.staff_bar = get_int("staff_bar")
            roz.staff_waiters = get_int("staff_waiters")
            roz.staff_kitchen = get_int("staff_kitchen")
            roz.staff_security = get_int("staff_security")

            # 📝 Notatka
            roz.notatka = request.form.get("notatka", "").strip()

            db_session.add(roz)
            db_session.commit()
            db_session.close()

            return redirect(url_for('daily_summary', data=data_str))

    return render_template('add_daily.html', default_date=default_date)


@app.route('/daily-added')
def daily_added():
    return render_template('daily_added.html')

@app.route('/daily-summary', methods=['GET'])
def daily_summary():
    db_session = Session()

    selected_month = int(request.args.get('month', datetime.date.today().month))
    selected_year = int(request.args.get('year', datetime.date.today().year))

    first_day = datetime.date(selected_year, selected_month, 1)
    if selected_month == 12:
        last_day = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)

    wszystkie_daty = [first_day + datetime.timedelta(days=i) for i in range((last_day - first_day).days + 1)]

    dni_miesiaca = []
    for d in wszystkie_daty:
        roz = db_session.query(RozliczenieDzien).filter_by(
            daily_date=d,
            lokal=get_current_lokal()
        ).first()

        if roz:
            suma_przychodow = sum([
                roz.revenue_bar or 0,
                roz.revenue_kitchen or 0,
                roz.revenue_entry or 0,
                roz.revenue_other or 0
            ])

            suma_kosztow = sum([
                roz.cost_bar or 0,
                roz.cost_waiters or 0,
                roz.cost_kitchen or 0,
                roz.cost_marketing or 0,
                roz.cost_security or 0,
                roz.cost_other or 0
            ])

            dni_miesiaca.append({
                'data': d,
                'status': '✔',
                'id': roz.id,
                'suma_przychodow': suma_przychodow,
                'suma_kosztow': suma_kosztow
            })
        else:
            dni_miesiaca.append({
                'data': d,
                'status': '✘',
                'suma_przychodow': None,
                'suma_kosztow': None
            })

    db_session.close()

    return render_template(
        'daily_summary.html',
        selected_month=selected_month,
        selected_year=selected_year,
        dni_miesiaca=dni_miesiaca
    )


@app.route('/monthly-summary')
def monthly_summary():
    today = date.today()
    selected_month = int(request.args.get('month', today.month))
    selected_year = int(request.args.get('year', today.year))

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
        RozliczenieDzien.lokal == get_current_lokal()
    ).all()

    total_revenue = sum([
        (r.revenue_bar or 0) +
        (r.revenue_kitchen or 0) +
        (r.revenue_entry or 0) +
        (r.revenue_other or 0)
        for r in rozliczenia
    ])

    income_breakdown = {
        "Bar": sum(r.revenue_bar or 0 for r in rozliczenia),
        "Kuchnia": sum(r.revenue_kitchen or 0 for r in rozliczenia),
        "Wejściówki": sum(r.revenue_entry or 0 for r in rozliczenia),
        "Inne": sum(r.revenue_other or 0 for r in rozliczenia),
    }

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
        Invoice.lokal == get_current_lokal()
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
    # Wskaźniki pracowników względem przychodów bar i kuchnia
    total_revenue_bar = sum(r.revenue_bar or 0 for r in rozliczenia)
    total_revenue_kitchen = sum(r.revenue_kitchen or 0 for r in rozliczenia)
    cost_bar = cost_by_category['obsługa baru']
    cost_kitchen = cost_by_category['obsługa kuchni']

    # --- Wskaźniki procentowe względem właściwych przychodów
    cost_percentage_by_category = {}

    cost_bar = cost_by_category.get('obsługa baru', 0)
    cost_kitchen = cost_by_category.get('obsługa kuchni', 0)

    cost_percentage_by_category['obsługa baru'] = round((cost_bar / total_revenue_bar) * 100,
                                                        1) if total_revenue_bar else 0.0
    cost_percentage_by_category['obsługa kuchni'] = round((cost_kitchen / total_revenue_kitchen) * 100,
                                                          1) if total_revenue_kitchen else 0.0

    # Pozostałe koszty względem całości
    for key in ['obsługa kelnerska', 'marketing', 'ochrona', 'inne', 'faktury']:
        value = cost_by_category.get(key, 0)
        cost_percentage_by_category[key] = round((value / total_revenue) * 100, 1) if total_revenue else 0.0

    # --- Faktury (do tabeli)
    invoices = db_session.query(Invoice).filter(
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date,
        Invoice.lokal == get_current_lokal()
    ).all()

    db_session.close()

    def color_for(value):
        if value < 30:
            return "🟢"
        elif value <= 40:
            return "🟡"
        else:
            return "🔴"

    summary = {
        'total_revenue': total_revenue,
        'total_costs': total_costs,
        'net_result': total_revenue - total_costs,
        'income_breakdown': income_breakdown,
        'cost_by_category': cost_by_category,
        'cost_percentage_by_category': cost_percentage_by_category,  # ← DODANE TO
        'foodcost_bar': {
            'value': round((cost_bar / total_revenue_bar) * 100, 1) if total_revenue_bar else 0.0,
            'color': color_for(round((cost_bar / total_revenue_bar) * 100, 1)) if total_revenue_bar else "⚪️"
        },
        'foodcost_kitchen': {
            'value': round((cost_kitchen / total_revenue_kitchen) * 100, 1) if total_revenue_kitchen else 0.0,
            'color': color_for(
                round((cost_kitchen / total_revenue_kitchen) * 100, 1)) if total_revenue_kitchen else "⚪️"
        },
        'foodcost_towar_bar': {'value': 0.0, 'color': "⚪️"},
        'foodcost_towar_kitchen': {'value': 0.0, 'color': "⚪️"},
    }

    def calc_foodcost(value, revenue):
        if revenue:
            percent = round(value / revenue * 100, 1)
            if percent < 30:
                color = "🟢"
            elif percent <= 40:
                color = "🟡"
            else:
                color = "🔴"
        else:
            percent = 0
            color = "⚠️"
        return {'value': percent, 'color': color}

    # --- Nowe wskaźniki: koszt obsługi / przychód
    cost_bar = sum(r.cost_bar or 0 for r in rozliczenia)
    cost_kitchen = sum(r.cost_kitchen or 0 for r in rozliczenia)

    revenue_bar = sum(r.revenue_bar or 0 for r in rozliczenia)
    revenue_kitchen = sum(r.revenue_kitchen or 0 for r in rozliczenia)

    # FOODCOST = faktury / utarg
    foodcost_goods_bar = sum(f.net_amount or 0 for f in invoices if
                             (f.category or '').lower() == 'towar' and (f.goods_type or '').lower() == 'bar')
    foodcost_goods_kitchen = sum(f.net_amount or 0 for f in invoices if
                                 (f.category or '').lower() == 'towar' and (f.goods_type or '').lower() == 'jedzenie')

    summary["foodcost_towar_bar"] = calc_foodcost(foodcost_goods_bar, revenue_bar)
    summary["foodcost_towar_kitchen"] = calc_foodcost(foodcost_goods_kitchen, revenue_kitchen)

    summary["foodcost_bar"] = calc_foodcost(cost_bar, revenue_bar)
    summary["foodcost_kitchen"] = calc_foodcost(cost_kitchen, revenue_kitchen)


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

    MONTHS_PL = {
        1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień",
        5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień",
        9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
    }

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
                month = int(month)
                year = int(year)
                start = datetime.date(year, month, 1)
                next_month = (start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
                end = next_month - datetime.timedelta(days=1)
                label = f"{MONTHS_PL[month]} {year}"
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
            RozliczenieDzien.lokal == get_current_lokal()
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

        # Wskaźnik ogólny – koszty pracowników / przychód
        staff_keys = ["Obsługa baru", "Obsługa kuchni", "Obsługa kelnerska", "Marketing"]
        total_staff_costs = sum(expense_breakdown.get(k, 0) for k in staff_keys)
        staff_costs_percent = (total_staff_costs / total_income * 100) if total_income else 0

        if staff_costs_percent < 30:
            color = "🟢"
        elif staff_costs_percent < 40:
            color = "🟡"
        else:
            color = "🔴"

        # Szczegółowe przychody
        total_bar_revenue = sum(r.revenue_bar or 0 for r in entries)
        total_kitchen_revenue = sum(r.revenue_kitchen or 0 for r in entries)

        # Wskaźniki procentowe względem właściwych przychodów
        cost_percentage_by_category = {}

        cost_bar = expense_breakdown['Obsługa baru']
        cost_percentage_by_category['Obsługa baru'] = round((cost_bar / total_bar_revenue) * 100,
                                                             1) if total_bar_revenue else 0.0

        cost_kitchen = expense_breakdown['Obsługa kuchni']
        cost_percentage_by_category['Obsługa kuchnia'] = round((cost_kitchen / total_kitchen_revenue) * 100,
                                                                1) if total_kitchen_revenue else 0.0

        for key in ['Obsługa kelnerska', 'Marketing', 'Ochrona', 'Inne']:
            value = expense_breakdown.get(key, 0)
            cost_percentage_by_category[key] = round((value / total_income) * 100, 1) if total_income else 0.0

        return render_template(
            "summary_period.html",
            summary={
                "range": label,
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "result": round(result, 2),
                "income_breakdown": income_breakdown,
                "expense_breakdown": expense_breakdown,
                "staff_costs_percent": round(staff_costs_percent, 1),
                "staff_costs_percent_color": color,
                "cost_percentage_by_category": cost_percentage_by_category
            },
            now=datetime.datetime.now()
        )

    return render_template("summary_period.html", summary=None, now=datetime.datetime.now())


@app.route('/edit-daily/<data>', methods=['GET', 'POST'])
def edit_daily(data):
    db_session = Session()
    data_obj = datetime.datetime.strptime(data, '%Y-%m-%d').date()
    roz = db_session.query(RozliczenieDzien).filter_by(
        daily_date=data_obj,
        lokal=get_current_lokal()
    ).first()

    if not roz:
        db_session.close()
        return "Rozliczenie dnia nie istnieje dla wybranego lokalu", 404

    if request.method == 'POST':
        def get_kwota(field):
            return float(request.form.get(f"{field}_kwota", 0)) if request.form.get(field) else 0

        def get_int(value):
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # Przychody
        roz.revenue_bar = get_kwota('sprzedaz_bar')
        roz.revenue_kitchen = get_kwota('sprzedaz_kuchnia')
        roz.revenue_entry = get_kwota('sprzedaz_wejsciowki')
        roz.revenue_other = get_kwota('sprzedaz_inne')

        # Koszty
        roz.cost_bar = get_kwota('koszt_bar')
        roz.cost_waiters = get_kwota('koszt_kelnerzy')
        roz.cost_kitchen = get_kwota('koszt_kuchnia')
        roz.cost_security = get_kwota('koszt_ochrona')
        roz.cost_marketing = get_kwota('koszt_marketing')
        roz.cost_marketing_comment = request.form.get('koszt_marketing_komentarz', '')
        roz.cost_other = get_kwota('koszt_inne')
        roz.cost_other_comment = request.form.get('koszt_inne_komentarz', '')

        # Liczba pracowników
        roz.staff_bar = get_int(request.form.get("staff_bar"))
        roz.staff_kitchen = get_int(request.form.get("staff_kitchen"))
        roz.staff_waiters = get_int(request.form.get("staff_waiters"))
        roz.staff_security = get_int(request.form.get("staff_security"))
        roz.notatka = request.form.get("notatka", "").strip()

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

        # Nowe dane – liczby pracowników
        'staff_bar': roz.staff_bar,
        'staff_kitchen': roz.staff_kitchen,
        'staff_waiters': roz.staff_waiters,
        'staff_security': roz.staff_security,
        'notatka': roz.notatka
    }

    db_session.close()
    return render_template('edit_daily.html', roz=roz_dict, data=data)

@app.route('/delete_daily/<data>', methods=['POST'])
def delete_daily(data):
    db_session = Session()
    data_obj = datetime.datetime.strptime(data, '%Y-%m-%d').date()

    roz = db_session.query(RozliczenieDzien).filter_by(
        daily_date=data_obj,
        lokal=get_current_lokal()
    ).first()

    if roz:
        db_session.delete(roz)
        db_session.commit()

    db_session.close()
    return redirect(url_for('daily_summary'))

@app.route('/sync-revenue')
def sync_revenue():
    db_session = Session()
    rozliczenia = db_session.query(RozliczenieDzien).filter_by(
        lokal=get_current_lokal()
    ).all()
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

@app.route('/view_daily/<int:id>')
def view_daily(id):
    db_session = Session()
    lokal = get_current_lokal()

    roz = db_session.query(RozliczenieDzien).filter_by(id=id, lokal=lokal).first()

    if not roz:
        return "Nie znaleziono rozliczenia", 404

    current_date = roz.daily_date

    # ⬅️ Poprzedni dzień
    prev = db_session.query(RozliczenieDzien).filter(
        RozliczenieDzien.lokal == lokal,
        RozliczenieDzien.daily_date < current_date
    ).order_by(RozliczenieDzien.daily_date.desc()).first()

    # ➡️ Następny dzień
    next = db_session.query(RozliczenieDzien).filter(
        RozliczenieDzien.lokal == lokal,
        RozliczenieDzien.daily_date > current_date
    ).order_by(RozliczenieDzien.daily_date.asc()).first()

    with open("utils/data/config.json") as f:
        config = json.load(f)

    # Przychody
    przychody = sum([
        roz.revenue_bar or 0,
        roz.revenue_kitchen or 0,
        roz.revenue_entry or 0,
        roz.revenue_other or 0
    ])

    # Koszty
    koszty = sum([
        roz.cost_bar or 0,
        roz.cost_waiters or 0,
        roz.cost_kitchen or 0,
        roz.cost_marketing or 0,
        roz.cost_security or 0,
        roz.cost_other or 0
    ])

    wynik = przychody - koszty

    # Wskaźniki
    def licz_wskaznik(koszt, prog):
        if not przychody:
            return {"value": 0, "color": "⚠️"}
        val = round((koszt or 0) / przychody * 100, 1)
        if val <= prog["zielony"]:
            color = "🟢"
        elif val <= prog["żółty"]:
            color = "🟡"
        else:
            color = "🔴"
        return {"value": val, "color": color}

    wskazniki = {
        "obsługa_bar": licz_wskaznik(roz.cost_bar, config.get("progi_koszt_bar", {"zielony": 15, "żółty": 20})),
        "obsługa_kuchnia": licz_wskaznik(roz.cost_kitchen, config.get("progi_koszt_kuchnia", {"zielony": 20, "żółty": 25})),
        "obsługa_kelnerska": licz_wskaznik(roz.cost_waiters, config.get("progi_koszt_kelnerzy", {"zielony": 10, "żółty": 15})),
        "marketing": licz_wskaznik(roz.cost_marketing, config.get("progi_koszt_marketing", {"zielony": 5, "żółty": 8}))
    }

    koszt_pracownikow = (
        (roz.cost_bar or 0) +
        (roz.cost_kitchen or 0) +
        (roz.cost_waiters or 0) +
        (roz.cost_marketing or 0)
    )

    if not przychody:
        wskaznik_pracownicy = {"value": 0, "color": "⚠️"}
    else:
        procent = round(koszt_pracownikow / przychody * 100, 1)
        kolor = (
            "🟢" if procent < 30 else
            "🟡" if procent <= 40 else
            "🔴"
        )
        wskaznik_pracownicy = {"value": procent, "color": kolor}

    elementy = {
        "Obsługa bar": roz.cost_bar or 0,
        "Obsługa kuchni": roz.cost_kitchen or 0,
        "Obsługa kelnerska": roz.cost_waiters or 0,
        "Marketing": roz.cost_marketing or 0
    }

    breakdown_sorted = sorted(
        [{"nazwa": k, "procent": round(v / przychody * 100, 1)} for k, v in elementy.items()],
        key=lambda x: x["procent"],
        reverse=True
    )


    liczba_pracownikow = {
        "bar": roz.staff_bar or 0,
        "kuchnia": roz.staff_kitchen or 0,
        "kelnerzy": roz.staff_waiters or 0,
        "ochrona": roz.staff_security or 0
    }

    db_session.close()

    return render_template(
        'view_daily.html',
        roz=roz,
        przychody=przychody,
        koszty=koszty,
        wynik=wynik,
        wskazniki=wskazniki,
        liczba_pracownikow=liczba_pracownikow,
        wskaznik_pracownicy=wskaznik_pracownicy,
        breakdown_sorted=breakdown_sorted,
        prev_id=prev.id if prev else None,
        next_id=next.id if next else None
    )


if __name__ == '__main__':
    app.run(debug=True)
