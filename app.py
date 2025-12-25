import os
import sqlite3
import uuid
import random
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'hackathon_secret_key'

# --- Rate Limiter Setup ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            description TEXT,
            location_name TEXT, 
            severity TEXT,
            latitude REAL,
            longitude REAL,
            image_path TEXT,
            status TEXT DEFAULT 'Pending',
            cleanup_image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ai_confidence INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report', methods=['GET', 'POST'])
@limiter.limit("3 per 10 minutes")  # RATE LIMIT: 3 reports per 10 mins
def report():
    if request.method == 'POST':
        # 1. CAPTCHA Verification
        user_answer = request.form.get('captcha_answer')
        correct_answer = session.get('captcha_correct')
        
        # Clear captcha from session to prevent replay
        session.pop('captcha_correct', None)
        
        if not user_answer or not correct_answer or int(user_answer) != correct_answer:
            flash('❌ Incorrect CAPTCHA answer. Are you human?', 'error')
            return redirect(url_for('report'))

        report_id = str(uuid.uuid4())[:8]
        description = request.form['description']
        location_name = request.form['location_name']
        severity = request.form['severity']
        
        # GPS
        lat = request.form.get('latitude', 0)
        lon = request.form.get('longitude', 0)

        # File Upload
        if 'image' not in request.files:
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            return redirect(request.url)
        if file:
            filename = secure_filename(f"{report_id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO reports (id, description, location_name, severity, latitude, longitude, image_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (report_id, description, location_name, severity, lat, lon, filename))
        conn.commit()
        conn.close()
        
        return render_template('report.html', success=True, report_id=report_id)
    
    # Generate new CAPTCHA for GET request
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session['captcha_correct'] = num1 + num2
    captcha_question = f"{num1} + {num2}"
    
    return render_template('report.html', captcha_question=captcha_question)

@app.route('/map')
def view_map():
    return render_template('map.html')

@app.route('/api/reports')
def get_reports():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM reports")
    all_reports = [dict(row) for row in c.fetchall()]
    conn.close()

    visible_reports = []
    now = datetime.now()
    
    for r in all_reports:
        # Show all non-resolved reports
        if r['status'] != 'Resolved':
            visible_reports.append(r)
            continue
            
        # For Resolved reports, check 24h window
        if r['updated_at']:
            try:
                # Handle potential format variations if needed, but we stick to str(datetime.now()) usually
                # str(datetime.now()) typically: '2023-10-27 10:30:00.123456'
                # Let's try to parse common format
                updated_at = datetime.strptime(r['updated_at'], '%Y-%m-%d %H:%M:%S.%f')
                if now - updated_at < timedelta(hours=24):
                    visible_reports.append(r)
            except ValueError:
                # Fallback if no microseconds
                try:
                    updated_at = datetime.strptime(r['updated_at'], '%Y-%m-%d %H:%M:%S')
                    if now - updated_at < timedelta(hours=24):
                        visible_reports.append(r)
                except:
                    pass # Invalid format -> hide
        # If updated_at is None (old resolved reports) -> hide immediately per request
        
    return jsonify(visible_reports)

@app.route('/status', methods=['GET', 'POST'])
def status():
    report_data = None
    if request.method == 'POST':
        report_id = request.form['report_id']
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM reports WHERE id=?", (report_id,))
        report_data = c.fetchone()
        conn.close()
    return render_template('status.html', report=report_data)

# --- ADMIN ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session: return redirect(url_for('admin_login'))
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT count(*) FROM reports")
    total = c.fetchone()[0]
    c.execute("SELECT count(*) FROM reports WHERE status='Pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT count(*) FROM reports WHERE status='In Progress'")
    progress = c.fetchone()[0]
    c.execute("SELECT count(*) FROM reports WHERE status='Resolved'")
    resolved = c.fetchone()[0]
    
    c.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 5")
    latest_reports = [dict(row) for row in c.fetchall()]
    conn.close()
    return render_template('admin/dashboard.html', total=total, pending=pending, progress=progress, resolved=resolved, latest_reports=latest_reports)

@app.route('/admin/reports')
def admin_reports():
    if 'admin' not in session: return redirect(url_for('admin_login'))
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM reports ORDER BY created_at DESC")
    reports = [dict(row) for row in c.fetchall()]
    conn.close()
    return render_template('admin/reports.html', reports=reports)

@app.route('/admin/report/<id>', methods=['GET', 'POST'])
def admin_report_detail(id):
    if 'admin' not in session: return redirect(url_for('admin_login'))
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        new_status = request.form['status']
        cleanup_file = request.files.get('cleanup_image')
        if cleanup_file:
            cleanup_filename = secure_filename(f"cleanup_{id}_{cleanup_file.filename}")
            cleanup_file.save(os.path.join(app.config['UPLOAD_FOLDER'], cleanup_filename))
            c.execute("UPDATE reports SET status=?, cleanup_image_path=?, updated_at=? WHERE id=?", (new_status, cleanup_filename, datetime.now(), id))
        else:
            c.execute("UPDATE reports SET status=?, updated_at=? WHERE id=?", (new_status, datetime.now(), id))
        conn.commit()
        return redirect(url_for('admin_report_detail', id=id))
    c.execute("SELECT * FROM reports WHERE id=?", (id,))
    report = c.fetchone()
    conn.close()
    return render_template('admin/report_detail.html', report=report)

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('report.html', error="🚫 Rate limit exceeded. Please wait a moment before reporting again."), 429

if __name__ == '__main__':
    app.run(debug=True)