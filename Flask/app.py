from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from datetime import datetime
from flask_cors import CORS
import mysql.connector
import re
from datetime import timedelta

app = Flask(__name__)
CORS(app)

# 🔐 Secret key and session config
app.secret_key = 'something_secure_123'  # Change this in production!
app.permanent_session_lifetime = timedelta(minutes=30)

# Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Rekha@1289',
    'database': 'salon'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# Routes
@app.route('/')
def index():
    return render_template('saloon.html')

@app.route('/categories')
def categories():
    return render_template('categories.html')

@app.route('/appoinment')
def appointment_page():
    return render_template('appoinment.html')

@app.route("/men")
def men():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, category, price FROM service WHERE gender = 'male'")
    services = cursor.fetchall()
    cursor.close()
    conn.close()

  
    grouped_services = {}
    for service in services:
        category = service['category']
        grouped_services.setdefault(category, []).append(service)

   
    return render_template("men.html", grouped_services=grouped_services)


@app.route("/woman")
def woman():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, category, price FROM service WHERE gender = 'female'")
    services = cursor.fetchall()
    cursor.close()
    conn.close()

    
    grouped_services = {}
    for service in services:
        category = service['category']
        grouped_services.setdefault(category, []).append(service)

   
    return render_template("woman.html", grouped_services=grouped_services)


@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    try:
        name = request.form.get('name')
        phone = request.form.get('phone')
        gender = request.form.get('gender')
        appointment_date = request.form.get('date')
        hour = request.form.get('hour')
        minute = request.form.get('minute')
        ampm = request.form.get('ampm')

        # Time conversion logic
        hour_int = int(hour)
        if ampm == "PM" and hour_int != 12:
            hour_int += 12
        elif ampm == "AM" and hour_int == 12:
            hour_int = 0
        appointment_time = f"{hour_int:02}:{minute}:00"

        services = request.form.getlist('services')
        sub_services = request.form.getlist('sub_services[]')
        services_str = ', '.join(services)
        sub_services_str = ', '.join(sub_services)

        payment_method = request.form.get('payment_method')
        payment_details = request.form.get('payment_details')

  
        try:
            total_amount = float(request.form.get('total_amount', 0))
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Invalid total amount"}), 400

       
        conn = get_db_connection()
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO appointment
            (name, phone, gender, services, sub_services, appointment_date, appointment_time, payment_method, payment_details, total_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            name, phone, gender, services_str, sub_services_str,
            appointment_date, appointment_time, payment_method, payment_details, total_amount
        ))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success"})

    except Exception as e:
        print("❌ Server error:", e)
        return jsonify({"status": "error", "message": "Server error"}), 500

@app.route('/get_total_price', methods=['POST'])
def get_total_price():
    print("✅ Endpoint hit")
    try:
        data = request.get_json()
        gender = data.get('gender')
        selected_services = data.get('services')  # ✅ Must match frontend key

        if not gender or not selected_services:
            return jsonify({'status': 'error', 'message': 'Gender and services are required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        placeholders = ', '.join(['%s'] * len(selected_services))
        query = f"""
            SELECT SUM(price) FROM service
            WHERE gender = %s AND name IN ({placeholders})
        """

        cursor.execute(query, [gender] + selected_services)
        result = cursor.fetchone()
        total_price = float(result[0]) if result[0] else 0.0

        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'total': total_price})

    except Exception as e:
        print("❌ Error in get_total_price:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500
 
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'pass123'


app.permanent_session_lifetime = timedelta(minutes=30)


@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

   
    cursor.execute("SELECT * FROM service")
    services = cursor.fetchall()

    
    name = request.args.get('name', '').strip()
    phone = request.args.get('phone', '').strip()
    date = request.args.get('date', '').strip()

   
    query = "SELECT * FROM appointment WHERE 1=1"
    params = []

    if name:
        query += " AND name LIKE %s"
        params.append(f"%{name}%")

    if phone:
        query += " AND phone LIKE %s"
        params.append(f"%{phone}%")

    if date:
        query += " AND appointment_date = %s"
        params.append(date)

    cursor.execute(query, params)
    appointments = cursor.fetchall()

    conn.close()
    return render_template("admin.html", services=services, appointments=appointments)


@app.route("/add_service", methods=["GET", "POST"])
def add_service():
    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        gender = request.form["gender"]
        price = request.form["price"]

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO service (name, category, gender, price) VALUES (%s, %s, %s, %s)",
                       (name, category, gender, price))  # ✅ Table name = service
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))
    return render_template("add_service.html")


@app.route("/edit_service/<int:service_id>", methods=["GET", "POST"])
def edit_service(service_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        cursor.execute("UPDATE service SET name=%s, price=%s WHERE id=%s", (name, price, service_id))  # ✅
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))

    cursor.execute("SELECT * FROM service WHERE id = %s", (service_id,))  # ✅
    service = cursor.fetchone()
    conn.close()
    return render_template("edit_service.html", service=service)


@app.route("/delete_service/<int:service_id>")
def delete_service(service_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM service WHERE id=%s", (service_id,))  # ✅
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('index'))  # Changed from login_page to index

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

       
        cursor.execute("SELECT * FROM service")
        services = cursor.fetchall()

      
        cursor.execute("""
            SELECT name, phone, gender, appointment_date, appointment_time,
                   sub_services, total_amount, payment_method, payment_details
            FROM appointment
            ORDER BY appointment_date DESC
        """)
        appointments = cursor.fetchall()  # ✅ This line was missing

        print("✅ Services from DB:", services)
        print("✅ Appointments from DB:", appointments)

        cursor.close()
        conn.close()

        return render_template('admin.html', services=services, appointments=appointments)
    
    except Exception as e:
        print("❌ Error in admin_dashboard:", e)
        return "Internal Server Error", 500



@app.route('/admin_login_ajax', methods=['POST'])
def admin_login_ajax():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid credentials'})



if __name__ == '__main__':
    app.run(debug=True)
