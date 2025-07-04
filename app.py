from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from utils.file_handler import handle_upload
from utils.building_lookup import get_buildings
import sqlite3
import os

# app.py - Flask application for QR code asset capture
# This application allows users to capture asset information using QR codes,
# upload photos, and store the data in a SQLite database.
# It also provides a web interface for users to interact with the application.

app = Flask(__name__)
app.secret_key = 'ubc-qr-secret'

# ✅ Updated Ubuntu server path for uploads
app.config['UPLOAD_FOLDER'] = '/home/gandrade/Capture_photos_upload'
app.config['SESSION_TYPE'] = 'filesystem'

SQLITE_DB_PATH = '/home/gandrade/assetcapture/data/QR_codes.db'

def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def start():
    buildings = get_buildings()
    building_code = session.get('building_code', '')
    asset_type = session.get('asset_type', '')
    return render_template('start.html', buildings=buildings, building_code=building_code, asset_type=asset_type)

@app.route('/capture', methods=['POST'])
def capture():
    qr_code = request.form.get('qr_code')
    building_code = request.form.get('building_code')
    asset_type = request.form.get('asset_type')

    if not qr_code or qr_code.strip() == "":
        return "⚠️ QR code must be scanned and all fields completed.", 400

    # Check if QR code already exists
    exists = False
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM QR_codes WHERE QR_code_ID = ?", (qr_code,))
        exists = cursor.fetchone()[0] > 0
        conn.close()
    except Exception as e:
        print("⚠️ Failed to check QR code on capture:", e)

    session['building_code'] = building_code
    session['asset_type'] = asset_type

    return render_template(
        'capture.html',
        qr_code=qr_code,
        building_code=building_code,
        asset_type=asset_type,
        qr_exists=exists
    )

@app.route('/submit', methods=['POST'])
def submit():
    data = request.form
    files = request.files
    result = handle_upload(data, files, app.config['UPLOAD_FOLDER'])

    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM QR_codes WHERE QR_code_ID = ?", (result['qr_code'],))
        exists = cursor.fetchone()[0] > 0
        if not exists:
            conn.execute("INSERT INTO QR_codes (QR_code_ID) VALUES (?)", (result['qr_code'],))
            conn.commit()
        else:
            print(f"⚠️ QR code {result['qr_code']} already exists. Skipping insert.")
        conn.close()
    except Exception as e:
        print("⚠️ Failed to insert QR code:", e)

    return render_template('success.html', qr_code=result['qr_code'], files_saved=result['files_saved'])

@app.route('/check_qr_code', methods=['POST'])
def check_qr_code():
    qr_code = request.json.get('qr_code')
    exists = False
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM QR_codes WHERE QR_code_ID = ?", (qr_code,))
        exists = cursor.fetchone()[0] > 0
        conn.close()
    except Exception as e:
        print("⚠️ Failed to check QR code:", e)
    return jsonify({'exists': exists})

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print("🚀 Flask app running...")
    print("🔗 Open your browser and go to: http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)
# Note: The app runs in debug mode for development purposes.
