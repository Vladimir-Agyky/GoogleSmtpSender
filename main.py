from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'SaltySalt09@'  # 암호화를 위한 시크릿 키 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# 사용자 모델 생성
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.String(100), unique=True, nullable=False)
    site_password = db.Column(db.String(100), nullable=False)
    smtp_email = db.Column(db.String(100), nullable=False)
    smtp_password = db.Column(db.String(100), nullable=False)

# 로그인 관련 설정
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        site_id = request.form['site_id']
        site_password = generate_password_hash(request.form['site_password'])
        smtp_email = request.form['smtp_email']
        smtp_password = request.form['smtp_password']
        user = User(site_id=site_id, site_password=site_password, smtp_email=smtp_email, smtp_password=smtp_password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        site_id = request.form['site_id']
        user = User.query.filter_by(site_id=site_id).first()
        if user and check_password_hash(user.site_password, request.form['site_password']):
            login_user(user)
            flash('Login successful!')
            return redirect(url_for('send_email'))
        else:
            flash('Login unsuccessful. Please check your credentials.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/send_email', methods=['GET', 'POST'])
@login_required
def send_email():
    if request.method == 'POST':
        receiver_email = request.form['receiver_email']
        subject = request.form['subject']
        message = request.form['message']

        # 이메일 내용
        msg = MIMEMultipart()
        msg['From'] = current_user.smtp_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        # SMTP 서버 설정
        smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
        smtp_server.starttls()
        smtp_server.login(current_user.smtp_email, current_user.smtp_password)

        # 이메일 전송
        smtp_server.send_message(msg)
        smtp_server.quit()

        flash('Email sent successfully!')
        return redirect(url_for('send_email'))
    return render_template('send_email.html')

if __name__ == '__main__':  
    with app.app_context():
        db.create_all()
    app.run(debug=True)
