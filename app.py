from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/add-daily', methods=['GET', 'POST'])
def add_daily():
    if request.method == 'POST':
        # Tu możesz sobie na razie wyświetlić dane w konsoli
        form_data = request.form.to_dict()
        print(form_data)  # print w konsoli dla testów

        # Docelowo: zapis do bazy danych

        return redirect(url_for('home'))  # wracamy na stronę główną
    return render_template('add_daily.html')

@app.route('/add-invoice', methods=['GET', 'POST'])
def add_invoice():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        print(form_data)  # Wypisze w terminalu dane z faktury

        # Docelowo: zapis do bazy danych

        return redirect(url_for('home'))  # Po zapisaniu wracamy na stronę główną
    return render_template('add_invoice.html')

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
