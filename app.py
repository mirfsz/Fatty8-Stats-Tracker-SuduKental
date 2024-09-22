from flask import Flask, render_template, request, send_file, redirect, url_for, session
import pandas as pd
from datetime import datetime
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')

STORAGE_DIR = os.getenv('STORAGE_DIR', '/tmp')  # Temp directory, will be recreated on every deploy
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'mathetinkacak')

SQUAD_MEMBERS = [
    "Muhammad Saifullah Azim Bin Yusoff", "Muhammad Syahirryzam Bin Aismaly",
    "Ahmad Irfan Bin Ahmad Sanusi", "Jovan Lai Hang Hwa", "Ng Shi Ping Jethro",
    "Muhammad Danish Bin Jumari", "Muhammad Irhan Bin Zainuddin",
    "Praaveen S/O Sivakumar", "Chan Wee Kiat", "Iain Jusztn Macalagay Mabilin",
    "Liu Jian Kai", "Lander Nicole Tacuyan Mercado", "Mizwan Bin Mangsor",
    "Mohammad Irshaad", "Mohamed Ahnaf Bagarib", "Irfan Mirzan",
    "Muhammad Irfan Bin Johari", "Mohamed Rifhan bin Mohamed Rizal Maricar",
    "Nitin Palaniappan Arun"
]

# Database Initialization with Logging
def init_db():
    print("Initializing the database...")
    os.makedirs(STORAGE_DIR, exist_ok=True)
    db_path = os.path.join(STORAGE_DIR, 'fitness_data.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Create tables if they don't exist
    c.execute('CREATE TABLE IF NOT EXISTS fitness_data (week INTEGER, name TEXT, date TEXT, entry_type TEXT, steps INTEGER, o2_level INTEGER, pushups INTEGER, pullups INTEGER, situps INTEGER, run_time TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS admin_settings (current_week INTEGER)')
    print("Tables created or already exist.")
    
    # Ensure the admin_settings table has a default week set
    c.execute('SELECT COUNT(*) FROM admin_settings')
    if c.fetchone()[0] == 0:
        print("Inserting default week into admin_settings...")
        c.execute('INSERT INTO admin_settings (current_week) VALUES (1)')  # Default week 1

    conn.commit()
    conn.close()

# Insert entry into the database
def insert_data(entry):
    db_path = os.path.join(STORAGE_DIR, 'fitness_data.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('INSERT INTO fitness_data VALUES (:week, :name, :date, :entry_type, :steps, :o2_level, :pushups, :pullups, :situps, :run_time, :status)', entry)
    conn.commit()
    conn.close()

# Retrieve data from the database
def get_data():
    db_path = os.path.join(STORAGE_DIR, 'fitness_data.db')
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM fitness_data", conn)
    conn.close()
    return df

# Get current week from the admin settings
def get_current_week():
    db_path = os.path.join(STORAGE_DIR, 'fitness_data.db')
    conn = sqlite3.connect(db_path)
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
    return render_template('form.html', squad_members=SQUAD_MEMBERS, current_week=current_week)

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
    
    submitted_data = {}
    for member in SQUAD_MEMBERS:
        member_data = latest_data[latest_data['name'] == member]
        if not member_data.empty:
            submitted_data[member] = member_data.to_dict('records')
        else:
            submitted_data[member] = None

    return render_template('admin_dashboard.html', submitted_data=submitted_data, latest_week=selected_week, all_weeks=df['week'].unique())

# Route to set the new week number
@app.route('/admin_set_week', methods=['POST'])
@admin_required
def admin_set_week():
    new_week = request.form['new_week']
    db_path = os.path.join(STORAGE_DIR, 'fitness_data.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('UPDATE admin_settings SET current_week = ?', (new_week,))
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
