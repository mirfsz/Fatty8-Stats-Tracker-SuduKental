from flask import Flask, render_template, request, send_file, redirect, url_for, session
import pandas as pd
from datetime import datetime
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key

STORAGE_DIR = os.getenv('STORAGE_DIR', '/tmp')
ADMIN_PASSWORD = "mathetinkacak"

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

def init_db():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    db_path = os.path.join(STORAGE_DIR, 'fitness_data.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Drop the existing table if it exists
    c.execute('DROP TABLE IF EXISTS fitness_data')
    # Create the table with the new schema
    c.execute('''CREATE TABLE fitness_data
                 (week INTEGER, name TEXT, date TEXT, entry_type TEXT, steps INTEGER, o2_level INTEGER, 
                  pushups INTEGER, pullups INTEGER, situps INTEGER, run_time TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def insert_data(entry):
    db_path = os.path.join(STORAGE_DIR, 'fitness_data.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''INSERT INTO fitness_data VALUES 
                 (:week, :name, :date, :entry_type, :steps, :o2_level, :pushups, :pullups, :situps, :run_time, :status)''',
              entry)
    conn.commit()
    conn.close()

def get_data():
    db_path = os.path.join(STORAGE_DIR, 'fitness_data.db')
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM fitness_data", conn)
    conn.close()
    return df

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        entry = {
            'week': request.form['week'],
            'name': request.form['name'],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'entry_type': request.form['entry_type'],
            'steps': request.form.get('steps', ''),
            'o2_level': request.form.get('o2_level', ''),
            'pushups': request.form.get('pushups', ''),
            'pullups': request.form.get('pullups', ''),
            'situps': request.form.get('situps', ''),
            'run_time': request.form.get('run_time', ''),
            'status': request.form.get('status', 'Active')
        }
        insert_data(entry)
        return "Data submitted successfully!"
    return render_template('form.html', squad_members=SQUAD_MEMBERS)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Incorrect password"
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    df = get_data()
    latest_week = df['week'].max()
    latest_data = df[df['week'] == latest_week]

    submitted_data = {}
    for member in SQUAD_MEMBERS:
        member_data = latest_data[latest_data['name'] == member]
        if not member_data.empty:
            submitted_data[member] = member_data.to_dict('records')
        else:
            submitted_data[member] = None

    return render_template('admin_dashboard.html', submitted_data=submitted_data, latest_week=latest_week)

@app.route('/export')
@admin_required
def export_excel():
    df = get_data()
    excel_file = os.path.join('/tmp', "squad_fitness_data.xlsx")
    with pd.ExcelWriter(excel_file) as writer:
        for week, group in df.groupby('week'):
            group.to_excel(writer, sheet_name=f'Week {week}', index=False)
    return send_file(excel_file, as_attachment=True)

# Initialize the database with the new schema
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
