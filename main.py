from flask import Flask, render_template, request, redirect, url_for, flash
from peewee import *
import pandas as pd
import plotly.express as px
import plotly.utils
import json
from datetime import date, datetime

# Database setup
db = SqliteDatabase('fitness.db')

class BaseModel(Model):
    class Meta:
        database = db

class Activity(BaseModel):
    Dati = DateTimeField(default=datetime.now)
    Veids = CharField()  # running, walking, cycling etc
    Ilgums = IntegerField()  # minutes
    Kalorijas = IntegerField()
    Attalums = FloatField()  # kilometers
    Sirddarbiba = IntegerField(null=True)  # average heart rate

class HealthMetric(BaseModel):
    date = DateTimeField(default=datetime.now)
    weight = FloatField()  # kg
    blood_pressure_sys = IntegerField()
    blood_pressure_dia = IntegerField()
    sleep_hours = FloatField()

db.connect()
db.create_tables([Activity, HealthMetric])

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Required for flash messages

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/activities', methods=['GET', 'POST'])
def activities():
    if request.method == 'POST':
        Activity.create(
            Veids=request.form['type'],
            Ilgums=int(request.form['duration']),
            Kalorijas=int(request.form['calories']),
            Attalums=float(request.form['distance']),
            Sirddarbiba=int(request.form['heart_rate'])
        )
        flash('Activity added successfully!')
        return redirect(url_for('activities'))

    activities = Activity.select().order_by(Activity.Dati.desc())
    return render_template('activities.html', activities=activities)

@app.route('/health', methods=['GET', 'POST'])
def health():
    if request.method == 'POST':
        HealthMetric.create(
            weight=float(request.form['weight']),
            blood_pressure_sys=int(request.form['bp_sys']),
            blood_pressure_dia=int(request.form['bp_dia']),
            sleep_hours=float(request.form['sleep'])
        )
        flash('Health metrics added successfully!')
        return redirect(url_for('health'))

    metrics = HealthMetric.select().order_by(HealthMetric.date.desc())
    return render_template('health.html', metrics=metrics)

@app.route('/analytics')
def analytics():
    # Activity analysis
    activities = list(Activity.select().dicts())
    df_activities = pd.DataFrame(activities)

    # Pārveidojam aktivitāšu veidus uz latvisko nosaukumu
    activity_types = {
        'skriešana': 'Skriešana',
        'iešana': 'Iešana',
        'riteņbraukšana': 'Riteņbraukšana',
        'peldēšana': 'Peldēšana'
    }

    if not df_activities.empty:
        df_activities['Veids'] = df_activities['Veids'].map(activity_types)
        # Create various visualizations
        # Kaloriju diagramma
        calories_by_type = px.bar(df_activities, 
                                x='Veids', 
                                y='Kalorijas',
                                title='Kopējās sadedzinātās kalorijas pa aktivitātēm',
                                color='Veids',
                                labels={'Veids': 'Aktivitātes veids', 'Kalorijas': 'Kalorijas'},
                                color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
        calories_by_type.update_layout(
            showlegend=True,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=14),
            title_x=0.5,
            bargap=0.2,
            yaxis=dict(gridcolor='lightgray', title_font=dict(size=14)),
            xaxis=dict(title_font=dict(size=14))
        )

        # Attāluma diagramma
        distance_over_time = px.line(df_activities,
                                   x='Dati',
                                   y='Attalums',
                                   title='Noietais/noskrietais attālums laika gaitā',
                                   labels={'Dati': 'Datums', 'Attalums': 'Attālums (km)'},
                                   color_discrete_sequence=['#4ECDC4'])
        distance_over_time.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=14),
            title_x=0.5,
            xaxis=dict(showgrid=True, gridcolor='lightgray', title_font=dict(size=14)),
            yaxis=dict(showgrid=True, gridcolor='lightgray', title_font=dict(size=14))
        )
        distance_over_time.update_traces(line_width=3, mode='lines+markers')

        # Sirdsdarbības diagramma
        df_heart_rate = df_activities[df_activities['Sirddarbiba'].notna()]
        if not df_heart_rate.empty:
            heart_rate_hist = px.scatter(df_heart_rate,
                                       x='Sirddarbiba',
                                       y='Ilgums',
                                       title='Treniņu intensitāte',
                                       labels={'Sirddarbiba': 'Sirdsdarbība (sitieni/min)',
                                              'Ilgums': 'Treniņa ilgums (min)',
                                              'Veids': 'Aktivitātes veids'},
                                       color='Veids',
                                       size='Ilgums',
                                       size_max=35,
                                       template='plotly_white')
            heart_rate_hist.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey')))
        heart_rate_hist.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=14),
            title_x=0.5,
            showlegend=True,
            xaxis=dict(showgrid=True, gridcolor='lightgray', title_font=dict(size=14)),
            yaxis=dict(showgrid=True, gridcolor='lightgray', title_font=dict(size=14))
        )

        plots = {
            'calories': json.dumps(calories_by_type, cls=plotly.utils.PlotlyJSONEncoder),
            'distance': json.dumps(distance_over_time, cls=plotly.utils.PlotlyJSONEncoder),
            'heart_rate': json.dumps(heart_rate_hist, cls=plotly.utils.PlotlyJSONEncoder)
        }
        return render_template('analytics.html', plots=plots)

    return render_template('analytics.html', plots=None)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            df = pd.read_csv(file)
            # Process CSV data and save to database
            for _, row in df.iterrows():
                try:
                    Activity.create(
                        Veids=str(row['tips']).strip(),
                        Ilgums=int(float(row['ilgums'])),
                        Kalorijas=int(float(row['kalorijas'])),
                        Attalums=float(row['distance']),
                        Sirddarbiba=int(float(row['sirdsdarbības ātrums']))
                    )
                except Exception as e:
                    print(f"Kļūda ieraksta {row['tips']} pievienošanā: {e}")
                    continue
            flash('Data uploaded successfully!')
            return redirect(url_for('activities'))
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
