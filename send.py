import smtplib
import imaplib
from email import encoders
from email.header import decode_header
from email.parser import BytesParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import chardet
import os, mimetypes
from werkzeug.utils import secure_filename

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

class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    from_name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()
    print("Database and tables created")

# 로그인 관련 설정
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None  # 오류 메시지를 저장할 변수 초기화
    if request.method == 'POST':
        site_id = request.form['site_id']
        if len(site_id) < 4:
            error_message = 'Username must be at least 4 characters long.'
        elif User.query.filter_by(site_id=site_id).first():
            error_message = 'Username already exists.'
        else:
            site_password = generate_password_hash(request.form['site_password'])
            smtp_email = request.form['smtp_email']
            smtp_password = request.form['smtp_password']
            user = User(site_id=site_id, site_password=site_password, smtp_email=smtp_email, smtp_password=smtp_password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
    return render_template('register.html', error_message=error_message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None  # 오류 메시지를 저장할 변수 초기화
    if request.method == 'POST':
        site_id = request.form['site_id']
        user = User.query.filter_by(site_id=site_id).first()
        if user and check_password_hash(user.site_password, request.form['site_password']):
            login_user(user)
            flash('Login successful!')
            return redirect(url_for('send_email'))
        else:
            error_message = 'Incorrect username or password. Please try again.'
    return render_template('login.html', error_message=error_message)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/send_email', methods=['GET', 'POST'])
@login_required
def send_email():
    messages = []
    if request.method == 'POST':
        receiver_email = request.form['receiver_email']
        subject = request.form['subject']
        message = request.form['message']
        anonymous = request.form.get('anonymous')

        attachment = request.files['file']
        if attachment:
            filename = secure_filename(attachment.filename)
            file_path = os.path.join(app.root_path, 'uploads', filename)
            attachment.save(file_path)

            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type is None:
                mime_type = 'application/octet-stream'
                
            # 첨부 파일 MIME 형식으로 변환
            part = MIMEBase(*mime_type.split('/', 1))
            with open(file_path, 'rb') as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {filename}')


        msg = MIMEMultipart()
        if anonymous:
            smtp_email = "unknownsender6974@gmail.com" 
            smtp_password = "fuptjkgqqovttuum"
        else:
            smtp_email = current_user.smtp_email
            smtp_password = current_user.smtp_password

        msg['From'] = smtp_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        if attachment:
            msg.attach(part)

        # SMTP 서버 설정 및 전송
        try:
            smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
            smtp_server.starttls()
            smtp_server.login(smtp_email, smtp_password)  

            smtp_server.send_message(msg)
            flash('이메일 전송 성공!')
            return redirect(url_for('send_email'))
        except Exception as e:
            messages.append(f"이메일 전송 중 오류가 발생했습니다: {e}")
        finally:
            smtp_server.quit()
        return redirect(url_for('send_email'))
    
    return render_template('send_email.html', messages=messages)


@app.route('/update')
@login_required
def update_mail():
    smtp_email = current_user.smtp_email
    smtp_password = current_user.smtp_password

    imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
    imap_server.login(smtp_email, smtp_password)
    imap_server.select('inbox')

    _, message_numbers = imap_server.search(None, 'ALL')
    messages = []
    messages_list = message_numbers[0].split()
    messages_list.reverse()  # 최신꺼를 위로 올리기
    if len(messages_list) > 20:
        messages_list = messages_list[:20]  # 띄울 개수
    print(messages_list)
    
    # 기존 Email 테이블 데이터 삭제
    Email.query.delete()
    db.session.commit()

    for num in messages_list:
        _, data = imap_server.fetch(num, '(RFC822)')
        msg = BytesParser().parsebytes(data[0][1])
        body = None
        
        # Decode the subject
        subject, encoding = decode_header(msg['subject'])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or 'utf-8', errors='replace')
        
        
        from_name, encoding = decode_header(msg['from'].replace('"', ''))[0]
        if isinstance(from_name, bytes):
            from_name = from_name.decode(encoding or 'utf-8', errors='replace')

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))

                if 'attachment' in content_disposition:
                    continue
                
                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    encoding = part.get_content_charset()
                    if encoding is None:
                        result = chardet.detect(payload)
                        encoding = result['encoding']
                    body = payload.decode(encoding, errors='replace')
                    break
                elif content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    encoding = part.get_content_charset()
                    if encoding is None:
                        result = chardet.detect(payload)
                        encoding = result['encoding']
                    body = payload.decode(encoding, errors='replace')
        else:
            payload = msg.get_payload(decode=True)
            encoding = msg.get_content_charset()
            if encoding is None:
                result = chardet.detect(payload)
                encoding = result['encoding']
            body = payload.decode(encoding, errors='replace') if payload else ""
        
        # 이메일 정보를 데이터베이스에 저장
        email = Email(
            subject=subject,
            from_name=from_name,
            date=msg['date'],
            body=body if body else "No Body Contents"
        )
        db.session.add(email)
        db.session.commit()
    imap_server.close()
    imap_server.logout()
    return redirect(url_for('inbox'))



@app.route('/inbox')
@login_required
def inbox():
    emails = Email.query.all()

    messages = []
    for email in emails:
        messages.append({
            'subject': email.subject,
            'from': email.from_name,
            'date': email.date,
            'body': email.body if email.body else "No Body Contents"
        })

    return render_template('inbox.html', messages=messages)

if __name__ == '__main__':
    app.run(debug=True)