from flask import Flask, render_template, request, redirect, url_for
from models import Activity, Health, create_db
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__)

# Izveidot datubāzi, ja tās vēl nav
create_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/activities')
def activity_view():
    activities = Activity.select()
    return render_template('activity_view.html', activities=activities)

@app.route('/health')
def health_view():
    health = Health.select()
    return render_template('health_view.html', health=health)

@app.route('/graphs')
def graph_view():
    # Datu sagatavošana aktivitātēm
    activities = Activity.select()
    df = pd.DataFrame([(a.date, a.steps, a.calories) for a in activities], columns=["Date", "Steps", "Calories"])
    
    # Izveidojiet grafiku
    fig = plt.figure(figsize=(6, 4))
    plt.plot(df['Date'], df['Steps'], label="Steps")
    plt.plot(df['Date'], df['Calories'], label="Calories", linestyle='--')
    plt.title("Physical Activity Over Time")
    plt.xlabel("Date")
    plt.ylabel("Value")
    plt.legend()
    
    # Saglabājiet grafiku un pārveidojiet to par attēlu
    img = BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    
    return render_template('graph_view.html', plot_url=plot_url)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            df = pd.read_csv(file)
            for _, row in df.iterrows():
                if 'steps' in row and 'calories' in row:
                    Activity.create(date=row['date'], steps=row['steps'], calories=row['calories'])
                if 'weight' in row and 'bp' in row:
                    Health.create(date=row['date'], weight=row['weight'], blood_pressure=row['bp'])
            return redirect(url_for('activity_view'))
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
