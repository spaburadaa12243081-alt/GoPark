from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt 

# --- Define the Flask App ---
app = Flask(__name__)
bcrypt = Bcrypt(app) 

# --- MySQL Database Configuration ---
# *** Confirmed Settings for WAMP ***
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

@app.route('/login', methods=['POST'])
def login():
    """Handles the login form submission by checking credentials against the database."""
    username_attempt = request.form.get('username')
    password = request.form.get('password')
    connection = create_db_connection()
    
    # Default message for internal server or connection error
    message = "Login failed: An internal server error occurred." 

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Retrieve the username and password hash.
            query = "SELECT username, password FROM users WHERE username = %s"
            cursor.execute(query, (username_attempt,))
            user_data = cursor.fetchone()

            if user_data:
                stored_hash = user_data['password']
                retrieved_username = user_data['username'] 
                
                # Check 1: User exists. Now check password.
                if bcrypt.check_password_hash(stored_hash, password):
                    print(f"User '{retrieved_username}' logged in successfully.")
                    # SUCCESS MESSAGE
                    message = f"Login successful! Welcome, {retrieved_username}!"
                else:
                    # FAILURE CASE 1: Correct username, Wrong password.
                    print(f"Login failed for user '{retrieved_username}': Invalid password.")
                    # Professional message for incorrect username or password for known users
                    message = "Login failed. Check your username and password."
            else:
                # FAILURE CASE 2: Username not found (user has not signed up).
                print(f"Login failed: User '{username_attempt}' not found in database.")
                message = "You need to Signup first."

            cursor.close()
        except Error as e:
            print(f"Database error during login: {e}")
            # If database error occurs, use the professional message for security and clarity
            message = "Login failed. Check your username and password."
        finally:
            connection.close()
            
    # Redirect back to the landing page (home)
    return redirect(url_for('landing_page', message=message))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Renders the signup page (GET) and handles new user creation (POST)."""
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password') 
        
        # Check if passwords match
        if password != confirm_password:
            message = "The password you entered in 'Create Password' is not the same as the user put in the 'Confirm Password'."
            return redirect(url_for('landing_page', message=message))
        
        # Hash the password before storing it
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        connection = create_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                # Insert the new user with the HASHED password
                insert_query = "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (name, hashed_password, email)) 
                connection.commit()
                print(f"New user '{name}' registered successfully.")
                
            except Error as e:
                if 'Duplicate entry' in str(e):
                    print(f"Database error during signup: User '{name}' or email '{email}' already exists.")
                    message = "Registration failed: Username or email already in use."
                else:
                    print(f"Database error during signup: {e}")
                    message = "Registration failed: A database error occurred."

            finally:
                connection.close()
        
        # Redirect to the login page after successful registration
        return redirect(url_for('landing_page', message='Registration successful. Please log in.'))
    
    # Renders the signup page for GET requests
    return render_template('signup.html')


# --- Run the Application ---
if __name__ == '__main__':
    print("\n\n--- GoPark! Landing Page Server Started ---")
    print("Open your browser to: http://127.0.0.1:5000/")
    print("------------------------------------------\n")
    app.run(debug=True, use_reloader=False)