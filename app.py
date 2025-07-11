from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import random
import string
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace in production

# ---------------------- Email Config ----------------------
EMAIL_ADDRESS = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("TODO_PASSWORD")

print("✅ EMAIL_USER:", EMAIL_ADDRESS)
print("✅ TODO_PASSWORD set:", bool(EMAIL_PASSWORD))

def send_verification_email(to_email, code):
    subject = "Your Verification Code - To-Do App"
    body = f"Hello,\n\nYour verification code is: {code}\n\nThanks for registering!"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
    except Exception as e:
        print(f"❌ Email failed: {e}")
        flash("❌ Failed to send verification email. Try again.", "error")

def test_email():
    print("🚀 Testing email setup...")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(
                EMAIL_ADDRESS,
                EMAIL_ADDRESS,
                "Subject: Test Email\n\nHello from your Flask To-Do App!"
            )
        print("✅ Test email sent successfully!")
    except Exception as e:
        print("❌ Email test failed:", e)

# ---------------------- File Paths ----------------------
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

USERS_FILE = os.path.join(DATA_DIR, 'users.json')

def sanitize_filename(username):
    return ''.join(c if c.isalnum() else '_' for c in username)

def get_user_file(username):
    safe = sanitize_filename(username)
    return os.path.join(DATA_DIR, f'tasks_{safe}.json')

# ---------------------- JSON Helpers ----------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
            return users if isinstance(users, dict) else {}
    except json.JSONDecodeError:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_tasks(username):
    filepath = get_user_file(username)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            tasks = json.load(f)
            return tasks if isinstance(tasks, list) else []
    except json.JSONDecodeError:
        return []

def save_tasks(username, tasks):
    with open(get_user_file(username), 'w') as f:
        json.dump(tasks, f, indent=4)

def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

# ---------------------- Routes ----------------------
@app.route('/')
def home():
    return render_template('welcome.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if username in users:
            flash("❌ Username already exists.", "error")
            return redirect(url_for('register'))

        if password != confirm:
            flash("❌ Passwords do not match.", "error")
            return redirect(url_for('register'))

        code = generate_verification_code()

        session['temp_user'] = username
        session['temp_pass'] = generate_password_hash(password)
        session['temp_email'] = email
        session['verify_code'] = code

        send_verification_email(email, code)
        flash("📧 Verification code sent to your email.", "success")
        return redirect(url_for('verify_email'))

    return render_template('register.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify_email():
    if request.method == 'POST':
        entered = request.form['code']
        correct = session.get('verify_code')
        username = session.get('temp_user')
        hashed_password = session.get('temp_pass')
        users = load_users()

        if entered == correct:
            users[username] = hashed_password
            save_users(users)
            session.pop('verify_code', None)
            session.pop('temp_user', None)
            session.pop('temp_pass', None)
            session.pop('temp_email', None)
            flash("✅ Registration successful. Please login.", "success")
            return redirect(url_for('login'))
        else:
            flash("❌ Incorrect verification code.", "error")
            return redirect(url_for('verify_email'))

    return render_template('verify.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']

        if username not in users:
            flash("❌ Username not found.", "error")
            return redirect(url_for('login'))

        if not check_password_hash(users[username], password):
            flash("❌ Incorrect password.", "error")
            return redirect(url_for('login'))

        session['username'] = username
        flash("✅ Logged in successfully.", "success")
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("👋 You’ve been logged out.", "success")
    return render_template('welcome.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

# ---------------------- Task API ----------------------
@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    username = session['username']

    if request.method == 'GET':
        return jsonify(load_tasks(username))

    if request.method == 'POST':
        data = request.get_json()
        tasks = load_tasks(username)
        new_task = {
            'id': len(tasks) + 1,
            'title': data['title'],
            'priority': data.get('priority', 'medium'),
            'due_date': data.get('due_date', ''),
            'category': data.get('category', ''),
            'done': False
        }
        tasks.append(new_task)
        save_tasks(username, tasks)
        return jsonify(new_task), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT', 'DELETE'])
def update_delete_task(task_id):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    username = session['username']
    tasks = load_tasks(username)
    task = next((t for t in tasks if t['id'] == task_id), None)

    if not task:
        return jsonify({'error': 'Task not found'}), 404

    if request.method == 'PUT':
        data = request.get_json()
        task.update({
            'title': data.get('title', task['title']),
            'priority': data.get('priority', task['priority']),
            'due_date': data.get('due_date', task['due_date']),
            'category': data.get('category', task['category']),
            'done': data.get('done', task['done'])
        })
        save_tasks(username, tasks)
        return jsonify(task)

    elif request.method == 'DELETE':
        tasks.remove(task)
        save_tasks(username, tasks)
        return jsonify({'message': 'Task deleted'})

@app.route('/api/tasks/clear', methods=['POST'])
def clear_completed_tasks():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    username = session['username']
    tasks = load_tasks(username)
    tasks = [t for t in tasks if not t['done']]
    save_tasks(username, tasks)
    return jsonify({'message': 'Completed tasks cleared'})

# ---------------------- Main ----------------------
if __name__ == '__main__':
    test_email()
    app.run(debug=True)
