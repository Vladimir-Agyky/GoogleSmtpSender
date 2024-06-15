import smtplib
import imaplib
from email.parser import BytesParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import html
import chardet

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
    messages = []  # 이 부분에서 messages 변수를 먼저 정의합니다.
    if request.method == 'POST':
        receiver_email = request.form['receiver_email']
        subject = request.form['subject']
        message = request.form['message']
        anonymous = request.form.get('anonymous')  # Check if anonymous checkbox is checked

        # 이메일 내용
        msg = MIMEMultipart()
        
        # 익명으로 보내기 체크되었는지 확인
        if anonymous:
            # 익명으로 보내기일 경우 미리 저장된 SMTP 자격 증명 사용
            smtp_email = "unknownsender6974@gmail.com"  # 미리 저장된 SMTP 이메일
            smtp_password = "fuptjkgqqovttuum"  # 미리 저장된 SMTP 비밀번호
        else:
            # 익명으로 보내지 않을 경우 현재 사용자의 SMTP 자격 증명 사용
            smtp_email = current_user.smtp_email
            smtp_password = current_user.smtp_password

        msg['From'] = smtp_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        # SMTP 서버 설정
        smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
        smtp_server.starttls()
        smtp_server.login(smtp_email, smtp_password)
        imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
        imap_server.login(smtp_email, smtp_password)
        imap_server.select('inbox')

        _, message_numbers = imap_server.search(None, 'ALL')

        for num in message_numbers[0].split():
            _, data = imap_server.fetch(num, '(RFC822)')
            msg = BytesParser().parsebytes(data[0][1])
            body = msg.get_payload(decode=True).decode('utf-8') if msg.get_payload(decode=True) else "" # 본문 가져오기
            messages.append({
                'subject': msg['subject'],
                'from': msg['from'],
                'date': msg['date'],
                'body': body
            })

        # IMAP 서버 연결 종료
        imap_server.close()
        imap_server.logout()

        # 이메일 전송
        smtp_server.send_message(msg)
        smtp_server.quit()

        flash('이메일 전송 성공!')
        return redirect(url_for('send_email'))
    return render_template('send_email.html', messages=messages)


from flask import render_template
from flask_login import login_required, current_user
import imaplib
import chardet
from email.parser import BytesParser
from email.header import decode_header

@app.route('/inbox')
@login_required
def inbox():
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
        
        
        
        
        messages.append({
            'subject': subject,
            'from': from_name,
            'date': msg['date'],
            'body': body if body else "No Body Contents"
        })

    imap_server.close()
    imap_server.logout()
    return render_template('inbox.html', messages=messages)

if __name__ == '__main__':
    app.run(debug=True)