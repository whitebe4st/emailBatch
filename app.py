from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import pandas as pd
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'csv'}

# Upload folders
UPLOAD_FOLDER_ATTACHMENTS = 'uploads/attachments'
UPLOAD_FOLDER_CSV = 'uploads/csv_files'

app.config['UPLOAD_FOLDER_ATTACHMENTS'] = UPLOAD_FOLDER_ATTACHMENTS
app.config['UPLOAD_FOLDER_CSV'] = UPLOAD_FOLDER_CSV

# Ensure upload directories exist
os.makedirs(UPLOAD_FOLDER_ATTACHMENTS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_CSV, exist_ok=True)

# Helper function to check allowed file extensions
def allowed_file(filename, filetype):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS and \
           filename.rsplit('.', 1)[1].lower() == filetype

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'email' in session:
        return redirect(url_for('email_ui'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    remember = request.form.get('remember')

    # Attempt to log in to the SMTP server to verify credentials
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Encrypt the connection
            server.login(email, password)  # Attempt to log in

        session['email'] = email
        session['password'] = password if remember else None

        return redirect(url_for('email_ui'))

    except smtplib.SMTPAuthenticationError:
        flash("Invalid email or app password. Please try again.", "danger")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('password', None)
    return redirect(url_for('index'))

@app.route('/email_ui')
def email_ui():
    if 'email' not in session:
        return redirect(url_for('index'))
    return render_template('email_ui.html', logged_in_email=session['email'])

@app.route('/upload_attachment', methods=['POST'])
def upload_attachment():
    if 'attachment' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['attachment']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename, 'pdf'):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER_ATTACHMENTS'], filename))
        return jsonify({'filename': filename}), 200
    else:
        return jsonify({'error': 'Invalid file type. Only PDF allowed.'}), 400

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'csv_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename, 'csv'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER_CSV'], filename)
        file.save(filepath)
        try:
            data = pd.read_csv(filepath)
            emails = data.iloc[:, 0].tolist()
            return jsonify({'emails': emails}), 200
        except Exception as e:
            return jsonify({'error': f'Failed to load CSV file: {e}'}), 400
    else:
        return jsonify({'error': 'Invalid file type. Only CSV allowed.'}), 400

@app.route('/send_emails', methods=['POST'])
def send_emails():
    if 'email' not in session:
        return jsonify({'error': 'User not logged in.'}), 401

    data = request.get_json()
    email_list = data.get('email_list')
    subject = data.get('subject')
    body = data.get('body')
    attachment_filename = data.get('attachment')

    if not subject or not body:
        return jsonify({'error': 'Please provide a subject and body for the email.'}), 400

    sender_email = session['email']
    sender_password = session.get('password')

    # If password not in session (user didn't select "Remember Me"), prompt for password
    if not sender_password:
        sender_password = data.get('password')
        if not sender_password:
            return jsonify({'error': 'Password required to send emails.'}), 400

    # Start a new thread to send emails
    thread = threading.Thread(target=send_emails_thread, args=(sender_email, sender_password, email_list, subject, body, attachment_filename))
    thread.start()

    return jsonify({'message': 'Emails are being sent.'}), 200

def send_emails_thread(sender_email, sender_password, email_list, subject, body, attachment_filename):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Encrypt the connection
            server.login(sender_email, sender_password)

            total_emails = len(email_list)
            for i, email in enumerate(email_list):
                # Create the email content
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                # Attach the PDF file if it exists
                if attachment_filename:
                    attachment_path = os.path.join(app.config['UPLOAD_FOLDER_ATTACHMENTS'], attachment_filename)
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as attachment_file:
                            part = MIMEText(attachment_file.read(), 'base64', 'utf-8')
                            part.add_header('Content-Disposition', f'attachment; filename={attachment_filename}')
                            msg.attach(part)

                # Send the email
                server.sendmail(sender_email, email, msg.as_string())

                # Optionally, you can implement a progress mechanism here (e.g., updating a database or cache)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    app.run(debug=True)
