# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import math

# --- Define the Flask App --- 
app = Flask(__name__)
app.secret_key = "supersecretkey"
bcrypt = Bcrypt(app)

# --- MySQL Database Configuration ---
db_config = {
    'host': 'localhost',
    'database': 'gopark',
    'user': 'root',
    'password': '',
    'port': '3306'
}

def create_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        flash(f"Database connection error: {e}", "error")
    return None

def close_db_connection(connection, cursor=None):
    if cursor:
        cursor.close()
    if connection:
        connection.close()

# -----------------------------
# Helper function to get reservation
# -----------------------------
def get_reservation_by_id(reservation_id):
    connection = create_db_connection()
    if not connection:
        return None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM reservations WHERE id = %s", (reservation_id,))
        return cursor.fetchone()
    finally:
        close_db_connection(connection, cursor)


# -------------------------------------------------------------------
# --- PAGES (Landing, About, Services, Contact) ---
# -------------------------------------------------------------------

@app.route('/')
def landing_page():
    username = request.cookies.get("username", "")
    message = request.args.get("message")
    return render_template('landing.html', message=message, username=username)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


# -------------------------------------------------------------------
# --- RESERVATION ---
# -------------------------------------------------------------------

@app.route('/reservation', methods=['GET', 'POST'])
def reservation_dashboard():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        vehicle_type = request.form.get('vehicle_type')
        plate_number = request.form.get('plate_number')
        reservation_date = request.form.get('reservation_date')
        arrival_time = request.form.get('arrival_time')
        departure_time = request.form.get('departure_time')
        parking_slot = request.form.get('parking_slot')
        total_minutes = request.form.get('total_minutes')

        today = datetime.now().date()
        selected_date = datetime.strptime(reservation_date, '%Y-%m-%d').date()

        if selected_date < today:
            return render_template('reservation.html', error="Cannot select a past date.")

        if selected_date == today:
            current_time = datetime.now().time()
            selected_arrival_time = datetime.strptime(arrival_time, '%H:%M').time()
            if selected_arrival_time < current_time:
                return render_template('reservation.html', error="Arrival time has already passed.")

        hourly_rate = 50 if vehicle_type.lower() in ['car', 'sedan', 'suv', 'hatchback'] else 30
        total_hours = int(total_minutes) / 60
        total_cost = math.ceil(total_hours * 4) / 4 * hourly_rate

        if not all([full_name, phone_number, email, vehicle_type, plate_number,
                    reservation_date, arrival_time, departure_time, parking_slot, total_minutes]):
            return render_template('reservation.html', error="All fields are required.")

        connection = create_db_connection()
        if not connection:
            return render_template('reservation.html', error="Cannot connect to database.")

        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO reservations 
                (full_name, phone_number, email, vehicle_type, plate_number,
                 reservation_date, arrival_time, departure_time, parking_slot,
                 total_minutes, total_cost, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
            """

            cursor.execute(query, (
                full_name, phone_number, email, vehicle_type, plate_number,
                reservation_date, arrival_time, departure_time, parking_slot,
                total_minutes, total_cost, datetime.now()
            ))

            connection.commit()
            reservation_id = cursor.lastrowid

            return redirect(url_for('payment_dashboard',
                                    reservation_id=reservation_id,
                                    total_cost=total_cost))

        finally:
            close_db_connection(connection, cursor)

    return render_template('reservation.html')


# -------------------------------------------------------------------
# --- PAYMENT PAGE ---
# -------------------------------------------------------------------

@app.route('/payment')
def payment_dashboard():
    reservation_id = request.args.get('reservation_id')
    total_cost = request.args.get('total_cost')

    reservation = get_reservation_by_id(reservation_id)
    if reservation:
        return render_template('payment.html', reservation=reservation, total_cost=total_cost)
    return "Reservation not found."


# -------------------------------------------------------------------
# --- LOGIN ---
# -------------------------------------------------------------------

@app.route('/login', methods=['POST'])
def login():
    username_attempt = request.form.get('username')
    password = request.form.get('password')

    # Admin login check
    if username_attempt.lower() == "goparkadmin@gmail.com" and password == "CSSgopark2025":
        response = make_response(redirect(url_for('admin_dashboard')))
        response.set_cookie("username", "Administrator", max_age=60*60*24)
        return response

    connection = create_db_connection()
    if not connection:
        return redirect(url_for('landing_page', message="Cannot connect to database."))

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username_attempt,))
        user_data = cursor.fetchone()

        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            response = make_response(redirect(url_for('reservation_dashboard')))
            response.set_cookie("username", user_data['username'], max_age=60*60*24)
            return response
        else:
            return redirect(url_for('landing_page', message="Incorrect username or password."))

    finally:
        close_db_connection(connection, cursor)


# -------------------------------------------------------------------
# --- SIGNUP ---
# -------------------------------------------------------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Prevent admin from signing up
        if email.lower() == "goparkadmin@gmail.com":
            return redirect(url_for('landing_page', message="Administrator accounts cannot be registered here. Please log in using the admin portal."))

        if password != confirm_password:
            return redirect(url_for('landing_page', message="Passwords do not match."))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        connection = create_db_connection()

        if not connection:
            return redirect(url_for('landing_page', message="Cannot connect to database."))

        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, password, created_at)
                VALUES (%s, %s, %s, %s)
            """, (username, email, hashed_password, datetime.now()))

            connection.commit()
            return redirect(url_for('landing_page', message="Account created! Please login."))

        finally:
            close_db_connection(connection, cursor)

    return render_template('signup.html')


# -------------------------------------------------------------------
# --- CONFIRM PAYMENT → SHOW SUMMARY PAGE ---
# -------------------------------------------------------------------

@app.route('/confirm-payment', methods=['POST'])
def confirm_payment():
    reservation_id = request.form['reservation_id']
    total_cost = request.form['total_cost']
    payment_method = request.form['payment_method']
    gcash_name = request.form.get('gcash_name', '')
    gcash_number = request.form.get('gcash_number', '')

    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return "Reservation not found.", 404

    # Save payment
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO payments
                (reservation_id, payment_method, account_number, account_name, amount, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (reservation_id, payment_method, gcash_number, gcash_name, float(total_cost), datetime.now()))

            cursor.execute("UPDATE reservations SET status = 'paid' WHERE id = %s", (reservation_id,))
            connection.commit()
        finally:
            close_db_connection(connection, cursor)

    username = request.cookies.get("username", "")

    return render_template(
        'summary.html',
        reservation={
            **reservation,
            "payment_method": payment_method,
            "gcash_name": gcash_name,
            "gcash_number": gcash_number
        },
        total_cost=total_cost,
        username=username
    )


# -------------------------------------------------------------------
# --- LOGOUT ---
# -------------------------------------------------------------------

@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('landing_page', message="Thank you!")))
    response.delete_cookie("username")
    return response


# -------------------------------------------------------------------
# --- RECEIPT PAGE ---
# -------------------------------------------------------------------

@app.route('/receipt/<int:payment_id>')
def receipt(payment_id):
    connection = create_db_connection()
    if not connection:
        return "Cannot connect to database.", 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM payments WHERE id = %s", (payment_id,))
        payment = cursor.fetchone()

        reservation = None
        if payment:
            cursor.execute("SELECT * FROM reservations WHERE id = %s", (payment['reservation_id'],))
            reservation = cursor.fetchone()

    finally:
        close_db_connection(connection, cursor)

    if not payment:
        return "Payment not found.", 404

    return render_template('receipt.html', payment=payment, reservation=reservation)


# -------------------------------------------------------------------
# --- ADMIN DASHBOARD (single-page with reservation list) ----------
# -------------------------------------------------------------------
@app.route('/admin/dashboard')
def admin_dashboard():
    connection = create_db_connection()
    if not connection:
        return "DB error", 500
    cursor = connection.cursor(dictionary=True)

    # ----- counters -----
    cursor.execute("SELECT COUNT(*) c FROM reservations")
    total_reservations = cursor.fetchone()['c']
    cursor.execute("SELECT COUNT(*) c FROM reservations WHERE status='pending'")
    pending_payments = cursor.fetchone()['c']
    cursor.execute("SELECT COUNT(*) c FROM reservations WHERE status='paid'")
    completed_payments = cursor.fetchone()['c']

    # ----- full reservation list -----
    cursor.execute("""SELECT id, full_name, phone_number, email, vehicle_type,
                             plate_number, reservation_date, arrival_time,
                             departure_time, parking_slot, total_cost, status
                      FROM reservations
                      ORDER BY reservation_date DESC, arrival_time DESC""")
    reservations = cursor.fetchall()

    # ----- custom form fields -----
    cursor.execute("SELECT * FROM custom_form_fields ORDER BY id")
    fields = cursor.fetchall()

    cursor.close()
    connection.close()

    username = request.cookies.get("username", "Administrator")
    return render_template('admin_dashboard.html',
                         total_reservations=total_reservations,
                         pending_payments=pending_payments,
                         completed_payments=completed_payments,
                         reservations=reservations,
                         fields=fields,
                         username=username)


# -------------------------------------------------------------------
# --- ADMIN: CUSTOMIZE USER PARKING RESERVATION FORM ---
# -------------------------------------------------------------------

@app.route('/admin/custom-form')
def admin_custom_form():
    connection = create_db_connection()
    if not connection:
        return "Database connection error."

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM custom_form_fields ORDER BY id ASC")
        fields = cursor.fetchall()
    finally:
        close_db_connection(connection, cursor)

    return render_template('admin_custom_form.html', fields=fields)


@app.route('/admin/add-field', methods=['POST'])
def admin_add_field():
    label = request.form.get('label')
    field_type = request.form.get('field_type')

    connection = create_db_connection()
    if not connection:
        return "Database connection error."

    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO custom_form_fields (label, field_type)
            VALUES (%s, %s)
        """, (label, field_type))
        connection.commit()
    finally:
        close_db_connection(connection, cursor)

    return redirect(url_for('admin_custom_form'))


@app.route('/admin/delete-field/<int:field_id>')
def admin_delete_field(field_id):
    connection = create_db_connection()
    if not connection:
        return "Database connection error."

    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM custom_form_fields WHERE id = %s", (field_id,))
        connection.commit()
    finally:
        close_db_connection(connection, cursor)

    return redirect(url_for('admin_custom_form'))


@app.route('/admin/edit-field/<int:field_id>', methods=['POST'])
def admin_edit_field(field_id):
    new_label = request.form.get('label')

    connection = create_db_connection()
    if not connection:
        return "Database connection error."

    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE custom_form_fields SET label = %s WHERE id = %s
        """, (new_label, field_id))
        connection.commit()
    finally:
        close_db_connection(connection, cursor)

    return redirect(url_for('admin_custom_form'))

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
