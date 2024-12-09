import mysql.connector
from mysql.connector import Error
from flask import Flask, request, jsonify
import bcrypt

app = Flask(__name__)

# Database Configuration // For higher security, this will be moved to a separate .env file and a dotenv loading method will be used to use it in this app.
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rAr02052004', 
    'database': 'eakbank'
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

# Testing Route
@app.route('/')
def index():
    return "EAK Bank Backend is Running"

# Test Connection with Database with an API request
@app.route('/api/test-db', methods=['GET'])
def test_db():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM branches")
        branches = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(branches), 200
    else:
        return jsonify({"error": "Database connection failed"}), 500
    
# Post API request to create an account for user X with currency X in branch X
@app.route('/api/account-create', methods=['POST'])
def account_create():
    data = request.json
    user_id = data.get('user_id')
    currency = data.get('currency')
    branch = data.get('branch')
    
    # Validate required fields
    if not user_id or not currency or not branch:
        return jsonify({"error": "Missing required fields"}), 400
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Check if branch exists in the branches table
        cursor.execute("SELECT * FROM branches WHERE name = %s", (branch,))
        branch_record = cursor.fetchone()
        if not branch_record:
            return jsonify({"error": "Invalid branch name"}), 400
        
        # Check if the user ID exists in the users table
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_record = cursor.fetchone()
        if not user_record:
            return jsonify({"error": "Invalid user ID"}), 400
        
        # Insert the account into the accounts table
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
    
    
# Post API to request login through website
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

# Post API to create a user with Hashed Password
@app.route('/api/create-user', methods=['POST'])
def create_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    # Password Hash Method
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
            
# Money transfer API (Between Accounts) - will implement a better way that automatically gets currency of the account and only allows same-currency account transfer
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
        
        # Check balances for the source account
        cursor.execute("SELECT balance FROM accounts WHERE id = %s AND currency = %s", (from_account_id, currency))
        from_account = cursor.fetchone()
        
        if not from_account or from_account['balance'] < amount:
            return jsonify({"error": "Insufficient balance"}), 400
        
        # Deduct from the source account
        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (amount, from_account_id))
        
        # Add to the target account
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (amount, to_account_id))
        
        # Log the transaction
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

# Query Branches / Connection with account and other APIs - TESTING PHRASE
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