from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt

# --- Define the Flask App ---
app = Flask(__name__)
bcrypt = Bcrypt(app)

# --- MySQL Database Configuration ---
db_config = {
    'host': 'localhost',
    'database': 'gopark',
    'user': 'root',
    'password': ''
}

def create_db_connection():
    """Attempts to create and return a MySQL database connection."""
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Successfully connected to MySQL Database!")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None
    return None


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

@app.route('/reservation')
def reservation_dashboard():
    """Reservation Dashboard"""
    return render_template('reservation.html')


# -------------------------------------------------------------------
# --- LOGIN ROUTE (updated & fixed) ---
# -------------------------------------------------------------------

@app.route('/login', methods=['POST'])
def login():
    username_attempt = request.form.get('username')
    password = request.form.get('password')
    connection = create_db_connection()
    
    message = "Login failed: An internal server error occurred."

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT username, password FROM users WHERE username = %s"
            cursor.execute(query, (username_attempt,))
            user_data = cursor.fetchone()

            if user_data:
                stored_hash = user_data['password']
                retrieved_username = user_data['username']
                
                if bcrypt.check_password_hash(stored_hash, password):
                    print(f"User '{retrieved_username}' logged in successfully.")
                    return redirect(url_for('reservation_dashboard'))
                else:
                    print("Incorrect password.")
                    message = "Login failed. Check your username or password."
            else:
                print("Username not found.")
                message = "User not found. Please sign up first."

            cursor.close()
        except Error as e:
            print(f"Database error during login: {e}")
            message = "Login failed. Check your credentials."
        finally:
            connection.close()
            
    return redirect(url_for('landing_page', message=message))


# -------------------------------------------------------------------
# --- SIGNUP ROUTE (FULLY FIXED) ---
# -------------------------------------------------------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':

        # FIXED: using username NOT name
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Password check
        if password != confirm_password:
            return redirect(url_for('landing_page',
                                    message="Passwords do not match."))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        connection = create_db_connection()
        if connection:
            try:
                cursor = connection.cursor()

                insert_query = """
                    INSERT INTO users (username, email, password)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(insert_query, (username, email, hashed_password))
                connection.commit()

                print(f"New user '{username}' registered successfully.")

                return redirect(url_for('landing_page',
                                        message="Account created successfully! Please login."))

            except Error as e:
                if "Duplicate entry" in str(e):
                    message = "Username or Email already exists."
                else:
                    message = "Database error occurred during signup."
                print(f"Signup Error: {e}")
                return redirect(url_for('landing_page', message=message))

            finally:
                connection.close()

        return redirect(url_for('landing_page',
                                message="Cannot connect to database."))

    return render_template('signup.html')


# --- Run the Application ---
if __name__ == '__main__':
    print("\n--- GoPark! Server Started ---")
    print("Open your browser at: http://127.0.0.1:5000")
    print("------------------------------------------\n")
    app.run(debug=True, use_reloader=False)
