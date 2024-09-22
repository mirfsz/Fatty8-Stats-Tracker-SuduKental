import os
import psycopg2
from urllib.parse import urlparse

from flask import Flask, render_template, request, send_file, redirect, url_for, session
import pandas as pd
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'mathetinkacak')

# Parse PostgreSQL connection URL from DATABASE_URL
result = urlparse(os.getenv('DATABASE_URL'))
username = result.username
password = result.password
database = result.path[1:]  # removes leading '/'
hostname = result.hostname
port = result.port

# Connect to PostgreSQL
def connect_db():
    return psycopg2.connect(
        dbname=database,
        user=username,
        password=password,
        host=hostname,
        port=port
    )

# Initialize the database (create tables if they don't exist)
def init_db():
    print("Initializing the PostgreSQL database...")
    conn = connect_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS fitness_data (
            week INTEGER, 
            name TEXT, 
            date TEXT, 
            entry_type TEXT, 
            steps INTEGER, 
            o2_level INTEGER, 
            pushups INTEGER, 
            pullups INTEGER, 
            situps INTEGER, 
            run_time TEXT, 
            status TEXT
        )
    ''')
    c.execute('CREATE TABLE IF NOT EXISTS admin_settings (current_week INTEGER)')
    
    # Ensure default week is set
    c.execute('SELECT COUNT(*) FROM admin_settings')
    if c.fetchone()[0] == 0:
        print("Inserting default week into admin_settings...")
        c.execute('INSERT INTO admin_settings (current_week) VALUES (1)')
    
    conn.commit()
    conn.close()
    print("PostgreSQL database initialized.")

# Insert fitness data into the database
def insert_data(entry):
    conn = connect_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO fitness_data (week, name, date, entry_type, steps, o2_level, pushups, pullups, situps, run_time, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (entry['week'], entry['name'], entry['date'], entry['entry_type'], entry['steps'], entry['o2_level'], entry['pushups'], entry['pullups'], entry['situps'], entry['run_time'], entry['status']))
    conn.commit()
    conn.close()

# Retrieve all fitness data
def get_data():
    conn = connect_db()
    df = pd.read_sql_query("SELECT * FROM fitness_data", conn)
    conn.close()
    return df

# Get current week from the admin settings
def get_current_week():
    conn = connect_db()
    c = conn.cursor()
    c.execute('SELECT current_week FROM admin_settings')
    week = c.fetchone()[0]
    conn.close()
    return week

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Main route for squad members to submit fitness data
@app.route('/', methods=['GET', 'POST'])
def index():
    current_week = get_current_week()  # Display current week for users
    if request.method == 'POST':
        entry = {
            'week': current_week,
            'name': request.form['name'],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'entry_type': request.form['entry_type'],
            'steps': request.form.get('steps', 0),
            'o2_level': request.form.get('o2_level', 0),
            'pushups': request.form.get('pushups', 0),
            'pullups': request.form.get('pullups', 0),
            'situps': request.form.get('situps', 0),
            'run_time': request.form.get('run_time', ''),
            'status': request.form.get('status', 'Active')
        }
        insert_data(entry)
        return "Data submitted successfully!"
    return render_template('form.html', current_week=current_week)

# Admin login route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Incorrect password"
    return render_template('admin_login.html')

# Admin dashboard displaying submitted data for the latest or selected week
@app.route('/admin_dashboard', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    df = get_data()
    
    if request.method == 'POST':  # Admin can select a specific week to view
        selected_week = int(request.form['selected_week'])
    else:
        selected_week = df['week'].max()  # Default to the latest week

    latest_data = df[df['week'] == selected_week]
    
    submitted_data = {row['name']: row for index, row in latest_data.iterrows()}

    return render_template('admin_dashboard.html', submitted_data=submitted_data, latest_week=selected_week, all_weeks=df['week'].unique())

# Route to set the new week number
@app.route('/admin_set_week', methods=['POST'])
@admin_required
def admin_set_week():
    new_week = request.form['new_week']
    conn = connect_db()
    c = conn.cursor()
    c.execute('UPDATE admin_settings SET current_week = %s', (new_week,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

# Export fitness data to Excel for a selected week
@app.route('/export/<int:week>')
@admin_required
def export_excel(week):
    df = get_data()
    week_data = df[df['week'] == week]
    excel_file = os.path.join('/tmp', f"squad_fitness_data_week_{week}.xlsx")
    week_data.to_excel(excel_file, index=False)
    return send_file(excel_file, as_attachment=True)

# Initialize the database on the first run
if __name__ == '__main__':
    init_db()  # Initialize the database
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
