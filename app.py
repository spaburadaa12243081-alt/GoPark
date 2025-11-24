from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import math
# --- Define the Flask App ---
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flashing messages
bcrypt = Bcrypt(app)

# --- MySQL Database Configuration (WAMP) ---
db_config = {
    'host': 'localhost',
    'database': 'gopark',
    'user': 'root',
    'password': '',  # Default WAMP password is empty
    'port': '3306'   # Default MySQL port in WAMP
}

def create_db_connection():
    """Create and return a MySQL database connection."""
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        flash(f"Database connection error: {e}", "error")
    return None

def close_db_connection(connection, cursor=None):
    """Safely close MySQL cursor and connection."""
    if cursor:
        cursor.close()
    if connection:
        connection.close()

# -------------------------------------------------------------------
# --- ROUTES (Page Rendering and Form Handling) ---
# -------------------------------------------------------------------

@app.route('/')
def landing_page():
    message = request.args.get('message')
    return render_template('landing.html', message=message)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/reservation', methods=['GET', 'POST'])
def reservation_dashboard():
    if request.method == 'POST':
        # Get form data
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
        
        # Validate date and time
        today = datetime.now().date()
        selected_date = datetime.strptime(reservation_date, '%Y-%m-%d').date()
        
        # Check if date is in the past
        if selected_date < today:
            return render_template('reservation.html', error="Cannot select a date in the past. Please choose today or a future date.")
        
        # Check if it's today but time has passed
        if selected_date == today:
            current_time = datetime.now().time()
            selected_arrival_time = datetime.strptime(arrival_time, '%H:%M').time()
            if selected_arrival_time < current_time:
                return render_template('reservation.html', error="Cannot select a time that has already passed for today. Please choose a future time.")
        
        # Calculate cost based on vehicle type and duration
        hourly_rate = 50 if vehicle_type.lower() in ['car', 'sedan', 'suv', 'hatchback'] else 30
        total_hours = int(total_minutes) / 60
        total_cost = math.ceil(total_hours * 4) / 4 * hourly_rate  # Round to nearest 0.25 hour
        
        # Validate required fields
        if not all([full_name, phone_number, email, vehicle_type, plate_number, 
                   reservation_date, arrival_time, departure_time, parking_slot, total_minutes]):
            return render_template('reservation.html', error="All fields are required.")
        
        # Save to database
        connection = create_db_connection()
        if not connection:
            return render_template('reservation.html', error="Cannot connect to database.")
        
        try:
            cursor = connection.cursor()
            insert_query = """
                INSERT INTO reservations 
                (full_name, phone_number, email, vehicle_type, plate_number, 
                 reservation_date, arrival_time, departure_time, parking_slot, 
                 total_minutes, total_cost, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
            """
            created_at = datetime.now()
            
            cursor.execute(insert_query, (
                full_name, phone_number, email, vehicle_type, plate_number,
                reservation_date, arrival_time, departure_time, parking_slot,
                total_minutes, total_cost, created_at
            ))
            connection.commit()
            
            reservation_id = cursor.lastrowid
            print(f"Reservation #{reservation_id} created successfully for {full_name}")
            print(f"Total minutes: {total_minutes}, Total cost: ₱{total_cost}")
            
            # Redirect to payment page with reservation details
            return redirect(url_for('payment_dashboard', 
                                  reservation_id=reservation_id,
                                  total_cost=total_cost))
            
        except Error as e:
            print(f"Reservation Error: {e}")
            return render_template('reservation.html', error=f"Database error: {e}")
        
        finally:
            close_db_connection(connection, cursor)
    
    return render_template('reservation.html')

@app.route('/payment')
def payment_dashboard():
    reservation_id = request.args.get('reservation_id')
    total_cost = request.args.get('total_cost')
    
    # Get reservation details from database
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM reservations WHERE id = %s"
            cursor.execute(query, (reservation_id,))
            reservation = cursor.fetchone()
            
            if reservation:
                return render_template('payment.html', 
                                     reservation=reservation,
                                     total_cost=total_cost)
            else:
                return "Reservation not found."
                
        except Error as e:
            print(f"Payment Error: {e}")
            return f"Error retrieving reservation: {e}"
        finally:
            close_db_connection(connection, cursor)
    
    return f"Payment page for reservation #{reservation_id} - Total: ₱{total_cost}"

# -------------------------------------------------------------------
# --- LOGIN ROUTE ---
# -------------------------------------------------------------------

@app.route('/login', methods=['POST'])
def login():
    username_attempt = request.form.get('username')
    password = request.form.get('password')
    connection = create_db_connection()
    
    if not connection:
        return redirect(url_for('landing_page', message="Cannot connect to database."))

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT username, password FROM users WHERE username = %s"
        cursor.execute(query, (username_attempt,))
        user_data = cursor.fetchone()

        if user_data:
            if bcrypt.check_password_hash(user_data['password'], password):
                print(f"User '{user_data['username']}' logged in successfully.")
                return redirect(url_for('reservation_dashboard'))
            else:
                print("Incorrect password.")
                return redirect(url_for('landing_page', message="Login failed. Check your username or password."))
        else:
            print("Username not found.")
            return redirect(url_for('landing_page', message="User not found. Please sign up first."))

    except Error as e:
        print(f"Database error during login: {e}")
        return redirect(url_for('landing_page', message=f"Database error: {e}"))

    finally:
        close_db_connection(connection, cursor)

# -------------------------------------------------------------------
# --- SIGNUP ROUTE ---
# -------------------------------------------------------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Password match check
        if password != confirm_password:
            return redirect(url_for('landing_page', message="Passwords do not match."))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        connection = create_db_connection()

        if not connection:
            return redirect(url_for('landing_page', message="Cannot connect to database."))

        try:
            cursor = connection.cursor()
            insert_query = """
                INSERT INTO users (username, email, password, created_at)
                VALUES (%s, %s, %s, %s)
            """
            created_at = datetime.now()
            cursor.execute(insert_query, (username, email, hashed_password, created_at))
            connection.commit()
            print(f"New user '{username}' registered successfully.")
            return redirect(url_for('landing_page', message="Account created successfully! Please login."))

        except Error as e:
            print(f"Signup Error: {e}")
            if "Duplicate entry" in str(e):
                message = "Username or Email already exists."
            else:
                message = f"Database error: {e}"
            return redirect(url_for('landing_page', message=message))

        finally:
            close_db_connection(connection, cursor)

    return render_template('signup.html')

# -------------------------------------------------------------------
# --- PAYMENT HANDLING ---
# -------------------------------------------------------------------

@app.route('/confirm-payment', methods=['POST'])
def confirm_payment():
    reservation_id = request.form.get('reservation_id')
    amount = request.form.get('amount') or request.form.get('total_cost') or 0
    gcash_number = request.form.get('gcash_number')
    gcash_name = request.form.get('gcash_name')

    if not reservation_id or not gcash_number or not gcash_name:
        return "Reservation ID, GCash number, and account name are required.", 400

    connection = create_db_connection()
    if not connection:
        return "Cannot connect to database.", 500

    try:
        cursor = connection.cursor()
        insert_payment_sql = """
            INSERT INTO payments (reservation_id, payment_method, account_number, account_name, amount, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        created_at = datetime.now()
        cursor.execute(insert_payment_sql, (
            reservation_id,
            'gcash',
            gcash_number,
            gcash_name,
            float(amount),
            created_at
        ))
        connection.commit()
        payment_id = cursor.lastrowid

        # Update reservation status
        cursor.execute("UPDATE reservations SET status = 'paid' WHERE id = %s", (reservation_id,))
        connection.commit()

        return redirect(url_for('receipt', payment_id=payment_id))

    finally:
        close_db_connection(connection, cursor)

# -------------------------------------------------------------------
# --- RECEIPT DISPLAY ---
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
        if payment and payment.get('reservation_id'):
            cursor.execute("SELECT * FROM reservations WHERE id = %s", (payment.get('reservation_id'),))
            reservation = cursor.fetchone()
        return render_template('receipt.html', payment=payment, reservation=reservation)
    finally:
        close_db_connection(connection, cursor)

# --- Run the Application ---
if __name__ == '__main__':
    print("\n--- GoPark! Server Started ---")
    print("Open your browser at: http://127.0.0.1:5000")
    print("------------------------------------------\n")
    app.run(debug=True, use_reloader=False)
