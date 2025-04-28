from flask import Flask, render_template, request, redirect, url_for
import os
from utils.pdf_reader import parse_invoice_from_pdf


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
        print(form_data)
        return redirect(url_for('home'))
    # Jeśli GET - pusty formularz
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


@app.route('/daily-summary')
def daily_summary():
    return "Strona Podsumowania dziennego - jeszcze w budowie."

@app.route('/weekly-summary')
def weekly_summary():
    return "Strona Podsumowania tygodniowego - jeszcze w budowie."

@app.route('/monthly-summary')
def monthly_summary():
    return "Strona Podsumowania miesięcznego - jeszcze w budowie."


if __name__ == '__main__':
    app.run(debug=True)
