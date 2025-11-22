from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt
from datetime import datetime

# --- Define the Flask App ---
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flashing messages
bcrypt = Bcrypt(app)

# --- MySQL Database Configuration ---
db_config = {
    'host': 'localhost',
    'database': 'gopark',
    'user': 'root',
    'password': ''
}

def create_db_connection():
    """Create and return a MySQL database connection."""
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
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
        
        # Validate required fields
        if not all([full_name, phone_number, email, vehicle_type, plate_number, 
                   reservation_date, arrival_time, departure_time, parking_slot]):
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
                 reservation_date, arrival_time, departure_time, parking_slot, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """
            cursor.execute(insert_query, (
                full_name, phone_number, email, vehicle_type, plate_number,
                reservation_date, arrival_time, departure_time, parking_slot
            ))
            connection.commit()
            
            reservation_id = cursor.lastrowid
            print(f"Reservation #{reservation_id} created successfully for {full_name}")
            
            # Redirect to payment page (you'll need to create this)
            return redirect(url_for('payment_dashboard', reservation_id=reservation_id))
            
        except Error as e:
            print(f"Reservation Error: {e}")
            return render_template('reservation.html', error=f"Database error: {e}")
        
        finally:
            close_db_connection(connection, cursor)
    
    return render_template('reservation.html')

@app.route('/payment')
def payment_dashboard():
    reservation_id = request.args.get('reservation_id')
    # You'll need to create a payment.html template
    return f"Payment page for reservation #{reservation_id} - To be implemented"


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
                INSERT INTO users (username, email, password)
                VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (username, email, hashed_password))
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


# --- Run the Application ---
if __name__ == '__main__':
    print("\n--- GoPark! Server Started ---")
    print("Open your browser at: http://127.0.0.1:5000")
    print("------------------------------------------\n")
    app.run(debug=True, use_reloader=False)