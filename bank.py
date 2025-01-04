import mysql.connector
from mysql.connector import Error
from flask import Flask, request, jsonify
from flask_cors import CORS
import bcrypt

app = Flask(__name__)
CORS(app)

# Database Configuration
db_config = {
    'host': 'MYSQL IP / DOMAIN',
    'user': 'MYSQL USER (with access to the db name below)',
    'password': 'MYSQL PASSWORD',
    'database': 'DB NAME'
}    

# Helper Function to Connect to MySQL DB
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

# Successful Connection Output
@app.route('/')
def index():
    return "EAK Bank Backend is Running"

# Create Account API
@app.route('/api/account-create', methods=['POST'])
def account_create():
    data = request.json
    user_id = data.get('user_id')
    currency = data.get('currency')
    branch = data.get('branch')

    if not user_id or not currency or not branch:
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM branches WHERE name = %s", (branch,))
        branch_record = cursor.fetchone()
        if not branch_record:
            return jsonify({"error": "Invalid branch name"}), 400

        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_record = cursor.fetchone()
        if not user_record:
            return jsonify({"error": "Invalid user ID"}), 400

        cursor.execute(
            "INSERT INTO accounts (user_id, currency, branch, balance) VALUES (%s, %s, %s, 0.00)",
            (user_id, currency, branch)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Account created successfully"}), 201
    else:
        return jsonify({"error": "Database connection failed"}), 500

# User Login API
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({"message": "Login successful", "user": user})
        else:
            return jsonify({"error": "Invalid username or password"}), 401
    else:
        return jsonify({"error": "Database connection failed"}), 500

# Create User API // Idea was that a banking agent will create the user of the customer and manually add data into db, but I've created an API instead.
@app.route('/api/create-user', methods=['POST'])
def create_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, hashed_password.decode('utf-8'))
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "User created successfully"}), 201
    else:
        return jsonify({"error": "Database connection failed"}), 500

# Transfers API
@app.route('/api/transfer', methods=['POST'])
def transfer():
    data = request.json
    from_account_id = data.get('from_account_id')
    to_account_id = data.get('to_account_id')
    amount = data.get('amount')
    currency = data.get('currency')

    if not from_account_id or not to_account_id or not amount or not currency:
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT balance FROM accounts WHERE id = %s AND currency = %s", (from_account_id, currency))
        from_account = cursor.fetchone()

        if not from_account or from_account['balance'] < amount:
            return jsonify({"error": "Insufficient balance"}), 400

        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (amount, from_account_id))
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (amount, to_account_id))

        cursor.execute(
            "INSERT INTO transactions (from_account_id, to_account_id, amount, currency, transaction_type) "
            "VALUES (%s, %s, %s, %s, 'transfer')",
            (from_account_id, to_account_id, amount, currency)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Transfer completed successfully"}), 200
    else:
        return jsonify({"error": "Database connection failed"}), 500

# Loan Application API
@app.route('/api/loan-apply', methods=['POST'])
def loan_apply():
    data = request.json
    user_id = data.get('user_id')
    amount = data.get('amount')
    duration = data.get('duration')

    if not user_id or not amount or not duration:
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT interest_rate FROM central_bank WHERE id = 1")
        central_bank_rate = cursor.fetchone()['interest_rate']
        bank_interest_rate = central_bank_rate + 2.0
        total_interest = (amount * bank_interest_rate * duration) / 100
        total_repayment = amount + total_interest

        cursor.execute(
            "INSERT INTO loans (user_id, amount, duration, interest_rate, total_repayment, status) "
            "VALUES (%s, %s, %s, %s, %s, 'pending')",
            (user_id, amount, duration, bank_interest_rate, total_repayment)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Loan application submitted successfully", "total_repayment": total_repayment}), 201
    else:
        return jsonify({"error": "Database connection failed"}), 500

# Credit Card Application API
@app.route('/api/credit-card-apply', methods=['POST'])
def credit_card_apply():
    data = request.json
    user_id = data.get('user_id')
    card_type = data.get('card_type')

    if not card_type:
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO credit_cards (user_id, card_type, status) VALUES (%s, %s, 'pending')",
            (user_id, card_type)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Credit card application submitted successfully"}), 201
    else:
        return jsonify({"error": "Database connection failed"}), 500

# Query Branches API
@app.route('/api/branches', methods=['GET'])
def get_branches():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name FROM branches")
        branches = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(branches), 200
    else:
        return jsonify({"error": "Database connection failed"}), 500

if __name__ == '__main__':
    print("Registered Routes:")
    for rule in app.url_map.iter_rules():
        methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
        print(f"{rule} -> Methods: [{methods}]")

    app.run(host='0.0.0.0', port=5000, debug=True)
