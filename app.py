from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import hashlib   # used for password hashing (discussed in class)
import re        # used for email/phone validation
import random    # used for OTP generation
import smtplib   # used for sending OTP email (Python standard library)
from email.mime.text import MIMEText          # for building email body
from email.mime.multipart import MIMEMultipart  # for building email structure

app = Flask(__name__)
app.jinja_env.globals['enumerate'] = enumerate  # allow {% for i, x in enumerate(list) %} in templates

# ----------------------------------------------------------------
# Secret key – used by Flask to sign session cookies
# ----------------------------------------------------------------
app.secret_key = 'quizmaster_secret_key'

# ----------------------------------------------------------------
# MySQL Configuration
# Uses environment variables for Render deployment, fallbacks for local dev
# ----------------------------------------------------------------
import os

app.config['MYSQL_HOST']     = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER']     = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'Varun23141')
app.config['MYSQL_DB']       = os.environ.get('MYSQL_DB', 'quizmaster')

mysql = MySQL(app)

# ----------------------------------------------------------------
# Email Configuration (Gmail SMTP)
# Use your Gmail address and an App Password
# Get App Password: myaccount.google.com → Security → App Passwords
# ----------------------------------------------------------------
EMAIL_ADDRESS  = 'your_gmail@gmail.com'   # <-- replace with your Gmail
EMAIL_PASSWORD = 'your_app_password'      # <-- replace with Gmail App Password


# ================================================================
#   HELPER: hash password using MD5 (simple, as discussed in class)
# ================================================================
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


# ================================================================
#   ROUTE: Landing Page
# ================================================================
@app.route('/')
def landing():
    return render_template('landing.html')


# ================================================================
#   ROUTE: User Login  (GET → show form | POST → process login)
# ================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = hash_password(request.form['password'])

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s',
                       (email, password))
        user = cursor.fetchone()

        if user:
            session['loggedin'] = True
            session['user_id']  = user['id']
            session['username'] = user['first_name']
            flash('Welcome back, ' + user['first_name'] + '!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Incorrect email or password. Please try again.', 'danger')

    return render_template('index.html')


# ================================================================
#   ROUTE: User Register  (GET → show form | POST → process)
# ================================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name        = request.form['first_name']
        last_name         = request.form['last_name']
        email             = request.form['email']
        phone             = request.form['phone']
        password          = hash_password(request.form['password'])
        confirm_password  = hash_password(request.form['confirm_password'])
        gender            = request.form['gender']

        # Validate passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('login'))

        # Validate phone (10 digits)
        if not re.match(r'^\d{10}$', phone):
            flash('Phone number must be exactly 10 digits.', 'danger')
            return redirect(url_for('login'))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if email already exists
        cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
        existing = cursor.fetchone()
        if existing:
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))

        # Insert new user into database
        cursor.execute(
            '''INSERT INTO users
               (first_name, last_name, email, phone, password, gender)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (first_name, last_name, email, phone, password, gender)
        )
        mysql.connection.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('index.html')


# ================================================================
#   ROUTE: Admin Login
# ================================================================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']   # plain text for default admin

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM admins WHERE email = %s AND password = %s',
                       (email, password))
        admin = cursor.fetchone()

        if admin:
            session['admin_loggedin'] = True
            session['admin_id']       = admin['id']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')

    return render_template('index.html')


# ================================================================
#   USER HELPER – login guard
# ================================================================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'loggedin' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ================================================================
#   ROUTE: User Dashboard
# ================================================================
@app.route('/dashboard')
@login_required
def user_dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT COUNT(*) AS cnt FROM quizzes')
    quiz_count = cursor.fetchone()['cnt']
    cursor.execute('SELECT COUNT(*) AS cnt FROM scores WHERE user_id=%s',
                   (session['user_id'],))
    attempt_count = cursor.fetchone()['cnt']
    cursor.execute('''SELECT s.score, s.total, q.title, s.attempted_at
                      FROM scores s JOIN quizzes q ON q.id=s.quiz_id
                      WHERE s.user_id=%s ORDER BY s.attempted_at DESC LIMIT 1''',
                   (session['user_id'],))
    last_attempt = cursor.fetchone()
    return render_template('user_dashboard.html',
                           username=session['username'],
                           quiz_count=quiz_count,
                           attempt_count=attempt_count,
                           last_attempt=last_attempt)


# ================================================================
#   BROWSE QUIZZES
# ================================================================
@app.route('/quizzes')
@login_required
def browse_quizzes():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT q.*, COUNT(qs.id) AS question_count
                      FROM quizzes q LEFT JOIN questions qs ON qs.quiz_id=q.id
                      GROUP BY q.id ORDER BY q.created_at DESC''')
    quizzes = cursor.fetchall()
    # Mark which quizzes the current user has already attempted
    cursor.execute('SELECT quiz_id, id AS score_id FROM scores WHERE user_id=%s',
                   (session['user_id'],))
    attempted = {row['quiz_id']: row['score_id'] for row in cursor.fetchall()}
    for q in quizzes:
        q['attempted']  = q['id'] in attempted
        q['score_id']   = attempted.get(q['id'])
    return render_template('user_quizzes.html', quizzes=quizzes)


# ================================================================
#   TAKE QUIZ
# ================================================================
@app.route('/quiz/<int:quiz_id>/take')
@login_required
def take_quiz(quiz_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM quizzes WHERE id=%s', (quiz_id,))
    quiz = cursor.fetchone()
    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('browse_quizzes'))
    # Prevent re-attempt
    cursor.execute('SELECT id FROM scores WHERE user_id=%s AND quiz_id=%s',
                   (session['user_id'], quiz_id))
    existing = cursor.fetchone()
    if existing:
        flash('You have already attempted this quiz. View your result below.', 'warning')
        return redirect(url_for('quiz_result', score_id=existing['id']))
    cursor.execute('SELECT * FROM questions WHERE quiz_id=%s', (quiz_id,))
    questions = list(cursor.fetchall())
    if not questions:
        flash('This quiz has no questions yet.', 'warning')
        return redirect(url_for('browse_quizzes'))
    # Randomize question order and option order if enabled
    option_map = {} # Maps quiz_id -> question_id -> displayed_key -> original_key
    if quiz.get('randomize', 1):
        random.shuffle(questions)
        for q in questions:
            # Original state
            original_opts = [('A', q['option_a']), ('B', q['option_b']),
                             ('C', q['option_c']), ('D', q['option_d'])]
            
            # Shuffle options
            shuffled_opts = list(original_opts)
            random.shuffle(shuffled_opts)
            
            # Create mapping for this question: what displayed key maps to what original key
            q_map = {}
            keys = ['A','B','C','D']
            
            for i, (orig_key, val) in enumerate(shuffled_opts):
                displayed_key = keys[i]
                q[f'option_{displayed_key.lower()}'] = val
                q_map[displayed_key] = orig_key
                
                # Update correct_option to the new displayed key so client-side / original scoring logic works
                # Actually, the DB stores the original correct_option ('B', etc.).
                # In submit_quiz, we compare chosen (mapped back) to original correct_option.
                if val == original_opts[ord(q['correct_option'])-65][1]:
                    # We don't change q['correct_option'] here anymore, we submit_quiz will check against original.
                    pass
            option_map[str(q['id'])] = q_map
            
    # Save the mapping to session so submit_quiz can translate choices back
    if option_map:
        session['quiz_map'] = option_map
    else:
        session.pop('quiz_map', None)

    # Pass total quiz time in seconds (time_limit is in minutes)
    quiz_time = int(quiz.get('time_limit', 10)) * 60
    return render_template('user_take_quiz.html', quiz=quiz,
                           questions=questions, quiz_time=quiz_time)


# ================================================================
#   SUBMIT QUIZ
# ================================================================
@app.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Guard: prevent double submit
    cursor.execute('SELECT id FROM scores WHERE user_id=%s AND quiz_id=%s',
                   (session['user_id'], quiz_id))
    if cursor.fetchone():
        flash('You have already submitted this quiz.', 'warning')
        return redirect(url_for('browse_quizzes'))

    cursor.execute('SELECT * FROM questions WHERE quiz_id=%s', (quiz_id,))
    questions = cursor.fetchall()

    score   = 0
    details = []

    # Retrieve option mapping if quiz was randomized
    option_map = session.get('quiz_map', {})

    for q in questions:
        # Get raw chosen key from form (this is the displayed key)
        raw_chosen = request.form.get(f'q_{q["id"]}', '').upper()
        
        # Translate to original DB key if mapping exists
        q_map = option_map.get(str(q['id']), {})
        chosen = q_map.get(raw_chosen, raw_chosen) if raw_chosen else ''
        
        correct    = q['correct_option'].upper()
        is_correct = (chosen == correct) and bool(chosen)
        
        if is_correct:
            score += 1
            
        details.append({
            'question':   q['question_text'],
            'option_a':   q['option_a'], 'option_b': q['option_b'],
            'option_c':   q['option_c'], 'option_d': q['option_d'],
            'chosen':     chosen, 'correct': correct, 'is_correct': is_correct
        })

    total = len(questions)

    # Save score
    cursor.execute(
        'INSERT INTO scores (user_id, quiz_id, score, total) VALUES (%s,%s,%s,%s)',
        (session['user_id'], quiz_id, score, total)
    )
    mysql.connection.commit()
    score_id = cursor.lastrowid

    # Save individual answers for review + analytics
    for q, d in zip(questions, details):
        cursor.execute(
            'INSERT INTO user_answers (score_id, question_id, chosen_option, is_correct) VALUES (%s,%s,%s,%s)',
            (score_id, q['id'], d['chosen'], int(d['is_correct']))
        )
    mysql.connection.commit()

    # Store details in session for immediate result display
    session['result_details'] = details
    return redirect(url_for('quiz_result', score_id=score_id))


# ================================================================
#   VIEW RESULT
# ================================================================
@app.route('/quiz/result/<int:score_id>')
@login_required
def quiz_result(score_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT s.*, q.title AS quiz_title, q.time_limit
                      FROM scores s JOIN quizzes q ON q.id=s.quiz_id
                      WHERE s.id=%s AND s.user_id=%s''',
                   (score_id, session['user_id']))
    result = cursor.fetchone()
    if not result:
        flash('Result not found.', 'danger')
        return redirect(url_for('user_dashboard'))

    details = session.pop('result_details', [])
    return render_template('user_result.html', result=result, details=details)


# ================================================================
#   QUIZ HISTORY
# ================================================================
@app.route('/history')
@login_required
def quiz_history():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT s.id, q.title AS quiz_title, s.score, s.total,
                             s.attempted_at,
                             ROUND(s.score/s.total*100,1) AS percentage
                      FROM scores s JOIN quizzes q ON q.id=s.quiz_id
                      WHERE s.user_id=%s ORDER BY s.attempted_at DESC''',
                   (session['user_id'],))
    history = cursor.fetchall()
    return render_template('user_history.html',
                           username=session['username'],
                           history=history)


# ================================================================
#   ADMIN HELPER – login guard
# ================================================================
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_loggedin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ================================================================
#   ADMIN DASHBOARD
# ================================================================
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT COUNT(*) AS cnt FROM quizzes')
    quiz_count = cursor.fetchone()['cnt']
    cursor.execute('SELECT COUNT(*) AS cnt FROM users')
    user_count = cursor.fetchone()['cnt']
    cursor.execute('SELECT COUNT(*) AS cnt FROM scores')
    result_count = cursor.fetchone()['cnt']
    return render_template('admin_dashboard.html',
                           quiz_count=quiz_count,
                           user_count=user_count,
                           result_count=result_count)


# ================================================================
#   CREATE QUIZ
# ================================================================
@app.route('/admin/create-quiz', methods=['GET', 'POST'])
@admin_required
def create_quiz():
    if request.method == 'POST':
        title             = request.form['title']
        num_questions     = int(request.form.get('num_questions', 10))
        description       = request.form.get('description', '')
        time_limit        = int(request.form.get('time_limit', 10))
        randomize         = int(request.form.get('randomize', 1))
        admin_id          = session['admin_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'INSERT INTO quizzes (title, num_questions, description, time_limit, randomize, created_by) VALUES (%s,%s,%s,%s,%s,%s)',
            (title, num_questions, description, time_limit, randomize, admin_id)
        )
        mysql.connection.commit()
        quiz_id = cursor.lastrowid
        flash('Quiz created! Now add questions.', 'success')
        return redirect(url_for('add_questions', quiz_id=quiz_id))
    return render_template('admin_create_quiz.html')


# ================================================================
#   ADD QUESTIONS (manual)
# ================================================================
@app.route('/admin/quiz/<int:quiz_id>/add-questions', methods=['GET', 'POST'])
@admin_required
def add_questions(quiz_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM quizzes WHERE id = %s', (quiz_id,))
    quiz = cursor.fetchone()
    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('manage_quizzes'))
    if request.method == 'POST':
        cursor.execute('SELECT COUNT(*) AS cnt FROM questions WHERE quiz_id=%s', (quiz_id,))
        current_count = cursor.fetchone()['cnt']
        if current_count >= quiz['num_questions']:
            flash(f'Limit reached! This quiz already has {current_count} questions.', 'warning')
        else:
            cursor.execute(
                'INSERT INTO questions (quiz_id,question_text,option_a,option_b,option_c,option_d,correct_option) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (quiz_id, request.form['question_text'], request.form['option_a'],
                 request.form['option_b'], request.form['option_c'], request.form['option_d'],
                 request.form['correct_option'].upper())
            )
            mysql.connection.commit()
            flash('Question added!', 'success')
    cursor.execute('SELECT * FROM questions WHERE quiz_id = %s', (quiz_id,))
    questions = cursor.fetchall()
    return render_template('admin_add_questions.html', quiz=quiz, questions=questions,
                           current_count=len(questions))


# ================================================================
#   UPLOAD QUESTIONS FROM .TXT
#   Format (blocks separated by blank lines):
#     Q: Question text
#     A: Option A
#     B: Option B
#     C: Option C
#     D: Option D
#     Correct: B
# ================================================================
@app.route('/admin/quiz/<int:quiz_id>/upload-questions', methods=['POST'])
@admin_required
def upload_questions(quiz_id):
    f = request.files.get('file')
    if not f or not f.filename.endswith('.txt'):
        flash('Please upload a valid .txt file.', 'danger')
        return redirect(url_for('add_questions', quiz_id=quiz_id))
    # Normalise Windows (\r\n) and old Mac (\r) line endings → \n
    content = f.read().decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
    blocks  = [b.strip() for b in content.strip().split('\n\n') if b.strip()]
    cursor  = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check remaining capacity
    cursor.execute('SELECT * FROM quizzes WHERE id=%s', (quiz_id,))
    quiz = cursor.fetchone()
    cursor.execute('SELECT COUNT(*) AS cnt FROM questions WHERE quiz_id=%s', (quiz_id,))
    existing = cursor.fetchone()['cnt']
    remaining = quiz['num_questions'] - existing

    added = 0
    for i, block in enumerate(blocks, 1):
        if added >= remaining:
            flash(f'Question limit reached ({quiz["num_questions"]}). Remaining blocks skipped.', 'warning')
            break
        try:
            lines = {l.split(':', 1)[0].strip().upper(): l.split(':', 1)[1].strip()
                     for l in block.splitlines() if ':' in l}
            cursor.execute(
                'INSERT INTO questions (quiz_id,question_text,option_a,option_b,option_c,option_d,correct_option) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (quiz_id, lines['Q'], lines['A'], lines['B'],
                 lines['C'], lines['D'], lines['CORRECT'].upper())
            )
            added += 1
        except Exception as e:
            flash(f'Block {i} skipped: {e}', 'warning')
    mysql.connection.commit()
    flash(f'{added} question(s) uploaded successfully!', 'success')
    return redirect(url_for('add_questions', quiz_id=quiz_id))


# ================================================================
#   MANAGE QUIZZES
# ================================================================
@app.route('/admin/quizzes')
@admin_required
def manage_quizzes():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT q.*, COUNT(qs.id) AS question_count
                      FROM quizzes q LEFT JOIN questions qs ON qs.quiz_id=q.id
                      GROUP BY q.id ORDER BY q.created_at DESC''')
    quizzes = cursor.fetchall()
    return render_template('admin_manage_quizzes.html', quizzes=quizzes)


# ================================================================
#   EDIT QUIZ
# ================================================================
@app.route('/admin/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_quiz(quiz_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM quizzes WHERE id = %s', (quiz_id,))
    quiz = cursor.fetchone()
    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('manage_quizzes'))
    if request.method == 'POST':
        cursor.execute(
            'UPDATE quizzes SET title=%s, num_questions=%s, description=%s, time_limit=%s WHERE id=%s',
            (request.form['title'], int(request.form.get('num_questions', 10)),
             request.form.get('description',''), request.form.get('time_limit',10), quiz_id)
        )
        mysql.connection.commit()
        flash('Quiz updated!', 'success')
        return redirect(url_for('manage_quizzes'))
    return render_template('admin_edit_quiz.html', quiz=quiz)


# ================================================================
#   DELETE QUIZ
# ================================================================
@app.route('/admin/quiz/<int:quiz_id>/delete', methods=['POST'])
@admin_required
def delete_quiz(quiz_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM quizzes WHERE id=%s', (quiz_id,))
    mysql.connection.commit()
    flash('Quiz deleted.', 'info')
    return redirect(url_for('manage_quizzes'))


# ================================================================
#   DELETE QUESTION
# ================================================================
@app.route('/admin/question/<int:q_id>/delete', methods=['POST'])
@admin_required
def delete_question(q_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT quiz_id FROM questions WHERE id=%s', (q_id,))
    row = cursor.fetchone()
    cursor.execute('DELETE FROM questions WHERE id=%s', (q_id,))
    mysql.connection.commit()
    flash('Question deleted.', 'info')
    return redirect(url_for('add_questions', quiz_id=row['quiz_id']))


# ================================================================
#   EDIT QUESTION
# ================================================================
@app.route('/admin/question/<int:q_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_question(q_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM questions WHERE id=%s', (q_id,))
    question = cursor.fetchone()
    if not question:
        flash('Question not found.', 'danger')
        return redirect(url_for('manage_quizzes'))
    if request.method == 'POST':
        cursor.execute(
            '''UPDATE questions SET question_text=%s, option_a=%s, option_b=%s,
               option_c=%s, option_d=%s, correct_option=%s WHERE id=%s''',
            (request.form['question_text'], request.form['option_a'],
             request.form['option_b'], request.form['option_c'],
             request.form['option_d'], request.form['correct_option'].upper(), q_id)
        )
        mysql.connection.commit()
        flash('Question updated!', 'success')
        return redirect(url_for('add_questions', quiz_id=question['quiz_id']))
    return render_template('admin_edit_question.html', question=question)


# ================================================================
#   MANAGE USERS
# ================================================================
@app.route('/admin/users')
@admin_required
def manage_users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT u.*, COUNT(s.id) AS quizzes_taken
                      FROM users u LEFT JOIN scores s ON s.user_id=u.id
                      GROUP BY u.id ORDER BY u.created_at DESC''')
    users = cursor.fetchall()
    return render_template('admin_manage_users.html', users=users)


# ================================================================
#   VIEW ALL RESULTS
# ================================================================
@app.route('/admin/results')
@admin_required
def admin_results():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT s.id, u.first_name, u.last_name, u.email,
                             q.title AS quiz_title,
                             s.score, s.total, s.attempted_at,
                             ROUND(s.score/s.total*100,1) AS percentage
                      FROM scores s
                      JOIN users u ON u.id=s.user_id
                      JOIN quizzes q ON q.id=s.quiz_id
                      ORDER BY s.attempted_at DESC''')
    results = cursor.fetchall()
    return render_template('admin_results.html', results=results)


# ================================================================
#   LOGOUT
# ================================================================
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ================================================================
#   ROUTE: Send OTP to Email  (called via fetch from JS)
# ================================================================
@app.route('/send-otp', methods=['POST'])
def send_otp():
    data  = request.get_json()          # receive JSON from JS fetch()
    email = data.get('email', '').strip()

    # Check if the email is registered
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()

    if not user:
        return jsonify({'success': False, 'message': 'Email not registered.'})

    # Generate 6-digit OTP and store in session
    otp = str(random.randint(100000, 999999))
    session['otp']         = otp
    session['otp_email']   = email

    # Send OTP via Gmail SMTP using smtplib
    try:
        msg = MIMEMultipart()
        msg['From']    = EMAIL_ADDRESS
        msg['To']      = email
        msg['Subject'] = 'QuizMaster - Your OTP for Password Reset'

        body = f'''Hello,

Your OTP for resetting your QuizMaster password is:

        {otp}

This OTP is valid for 10 minutes. Do not share it with anyone.

Regards,
QuizMaster Team'''
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()                              # encrypt connection
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)    # authenticate
        server.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        server.quit()

        return jsonify({'success': True, 'message': 'OTP sent to ' + email})

    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to send email: ' + str(e)})


# ================================================================
#   ROUTE: Reset Password  (called via fetch from JS)
# ================================================================
@app.route('/reset-password', methods=['POST'])
def reset_password():
    data         = request.get_json()
    otp_entered  = data.get('otp', '').strip()
    new_password = data.get('new_password', '')

    # Validate OTP from session
    if 'otp' not in session:
        return jsonify({'success': False, 'message': 'OTP expired. Please request a new one.'})

    if otp_entered != session['otp']:
        return jsonify({'success': False, 'message': 'Invalid OTP. Please try again.'})

    # Update password in database
    email           = session['otp_email']
    hashed_password = hash_password(new_password)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('UPDATE users SET password = %s WHERE email = %s',
                   (hashed_password, email))
    mysql.connection.commit()

    # Clear OTP from session
    session.pop('otp', None)
    session.pop('otp_email', None)

    return jsonify({'success': True, 'message': 'Password reset successful!'})




# ================================================================
#   LEADERBOARD  (global top 20 + per-quiz)
# ================================================================
@app.route('/leaderboard')
@login_required
def leaderboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Global: best score per user per quiz, ranked by %
    cursor.execute('''
        SELECT u.first_name, u.last_name, u.profile_picture,
               q.title AS quiz_title,
               s.score, s.total,
               ROUND(s.score/s.total*100,1) AS percentage
        FROM scores s
        JOIN users u  ON u.id  = s.user_id
        JOIN quizzes q ON q.id = s.quiz_id
        ORDER BY percentage DESC, s.score DESC
        LIMIT 20
    ''')
    global_top = cursor.fetchall()

    # All quizzes for the filter dropdown
    cursor.execute('SELECT id, title FROM quizzes ORDER BY title')
    quizzes = cursor.fetchall()

    # Per-quiz leaderboard (optional quiz_id param)
    quiz_id  = request.args.get('quiz_id', type=int)
    quiz_top = []
    selected_quiz = None
    if quiz_id:
        cursor.execute('SELECT title FROM quizzes WHERE id=%s', (quiz_id,))
        selected_quiz = cursor.fetchone()
        cursor.execute('''
            SELECT u.first_name, u.last_name, u.profile_picture,
                   s.score, s.total,
                   ROUND(s.score/s.total*100,1) AS percentage, s.attempted_at
            FROM scores s JOIN users u ON u.id=s.user_id
            WHERE s.quiz_id=%s
            ORDER BY percentage DESC, s.score DESC LIMIT 20
        ''', (quiz_id,))
        quiz_top = cursor.fetchall()

    return render_template('user_leaderboard.html',
                           global_top=global_top, quizzes=quizzes,
                           quiz_top=quiz_top, selected_quiz=selected_quiz,
                           quiz_id=quiz_id)


# ================================================================
#   PROFILE  – view & edit
# ================================================================
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER  = os.path.join('static', 'uploads')
ALLOWED_EXTS   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTS

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name  = request.form.get('last_name',  '').strip()
        phone      = request.form.get('phone',      '').strip()
        bio        = request.form.get('bio',        '').strip()

        # Handle profile picture upload
        pic_filename = None
        file = request.files.get('profile_picture')
        if file and file.filename and allowed_file(file.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            pic_filename = f"user_{session['user_id']}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_FOLDER, pic_filename))

        if pic_filename:
            cursor.execute(
                '''UPDATE users SET first_name=%s, last_name=%s, phone=%s,
                   bio=%s, profile_picture=%s WHERE id=%s''',
                (first_name, last_name, phone, bio, pic_filename, session['user_id'])
            )
        else:
            cursor.execute(
                'UPDATE users SET first_name=%s, last_name=%s, phone=%s, bio=%s WHERE id=%s',
                (first_name, last_name, phone, bio, session['user_id'])
            )
        mysql.connection.commit()
        session['username'] = first_name   # refresh navbar name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    cursor.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
    user = cursor.fetchone()

    # Stats for profile page
    cursor.execute('SELECT COUNT(*) AS cnt FROM scores WHERE user_id=%s', (session['user_id'],))
    quiz_count = cursor.fetchone()['cnt']
    cursor.execute('''SELECT ROUND(AVG(score/total*100),1) AS avg_pct
                      FROM scores WHERE user_id=%s''', (session['user_id'],))
    row = cursor.fetchone()
    avg_pct = row['avg_pct'] if row['avg_pct'] else 0

    return render_template('user_profile.html', user=user,
                           quiz_count=quiz_count, avg_pct=avg_pct)

# ================================================================
#   DELETE ACCOUNT
# ================================================================
@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    user_id = session.get('user_id')
    
    # Delete the user; cascade delete will handle related records in child tables
    cursor.execute('DELETE FROM users WHERE id=%s', (user_id,))
    mysql.connection.commit()
    
    # Clear the session
    session.clear()
    flash('Your account has been successfully deleted.', 'success')
    return redirect(url_for('landing'))


# ================================================================
#   QUIZ REVIEW MODE  – view any past attempt's full answer breakdown
# ================================================================
@app.route('/quiz/review/<int:score_id>')
@login_required
def quiz_review(score_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT s.*, q.title AS quiz_title
                      FROM scores s JOIN quizzes q ON q.id=s.quiz_id
                      WHERE s.id=%s AND s.user_id=%s''',
                   (score_id, session['user_id']))
    result = cursor.fetchone()
    if not result:
        flash('Review not found.', 'danger')
        return redirect(url_for('quiz_history'))

    cursor.execute('''
        SELECT ua.chosen_option, ua.is_correct,
               q.question_text, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_option
        FROM user_answers ua
        JOIN questions q ON q.id = ua.question_id
        WHERE ua.score_id = %s
        ORDER BY ua.id
    ''', (score_id,))
    answers = cursor.fetchall()

    return render_template('user_review.html', result=result, answers=answers)


# ================================================================
#   ADMIN – QUIZ ANALYTICS
# ================================================================
@app.route('/admin/quiz/<int:quiz_id>/analytics')
@admin_required
def quiz_analytics(quiz_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM quizzes WHERE id=%s', (quiz_id,))
    quiz = cursor.fetchone()
    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('manage_quizzes'))

    # Overall stats
    cursor.execute('''
        SELECT COUNT(*) AS attempts,
               ROUND(AVG(score/total*100),1) AS avg_pct,
               SUM(CASE WHEN score/total>=0.5 THEN 1 ELSE 0 END) AS passes,
               MAX(score) AS top_score,
               MIN(score) AS low_score,
               total
        FROM scores WHERE quiz_id=%s
    ''', (quiz_id,))
    stats = cursor.fetchone()

    # Per-question miss count using user_answers
    cursor.execute('''
        SELECT q.question_text, q.correct_option,
               COUNT(ua.id)      AS total_answers,
               SUM(CASE WHEN ua.is_correct=0 THEN 1 ELSE 0 END) AS wrong_count,
               ROUND(SUM(CASE WHEN ua.is_correct=0 THEN 1 ELSE 0 END)/COUNT(ua.id)*100,1) AS miss_rate
        FROM questions q
        LEFT JOIN user_answers ua ON ua.question_id=q.id
        WHERE q.quiz_id=%s
        GROUP BY q.id
        ORDER BY miss_rate DESC
    ''', (quiz_id,))
    question_stats = cursor.fetchall()

    return render_template('admin_quiz_analytics.html',
                           quiz=quiz, stats=stats, question_stats=question_stats)


# ================================================================
#   Run the app
# ================================================================
if __name__ == '__main__':
    app.run(debug=True)
