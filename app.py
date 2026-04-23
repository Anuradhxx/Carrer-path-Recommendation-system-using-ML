from flask import Flask, render_template, request, redirect, session
import mysql.connector
import os
import re


app = Flask(__name__)
app.secret_key = os.urandom(24)

# conn=mysql.connector.connect(
#     host="localhost",
#     user="root",          
#     password="",  
#     database="smart_career_database"
# )

# cursor = conn.cursor()


def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="smart_career_database",
        port=3306
    )





@app.route('/')
def home():
    if 'Id' in session:
        return redirect('/dashboard')
    return render_template('index.html')

@app.route('/register')
def register():
    if 'Id' in session:
        return redirect('/dashboard')
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'Id' in session:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT fName FROM users WHERE Id=%s", (session['Id'],))
        user = cursor.fetchone()

        cursor.execute("""
        SELECT COUNT(DISTINCT quiz_id) 
        FROM quiz_results 
        WHERE user_id=%s
        """, (session['Id'],))

        quiz_count = cursor.fetchone()[0]

        cursor.execute("""
        SELECT title, match_score 
        FROM recommendations r
        JOIN careers c ON r.career_id = c.id
        WHERE r.user_id=%s
        ORDER BY match_score DESC
        LIMIT 1
        """, (session['Id'],))

        top_career = cursor.fetchone()

        # total skills tracked
        cursor.execute("SELECT COUNT(*) FROM user_skills WHERE user_id=%s", (session['Id'],))
        skill_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return render_template('dashboard.html', user={'fName': user[0]}, quiz_count=quiz_count, top_career=top_career ,
                                                                            skill_count=skill_count)
    else:
        return redirect('/register')


@app.route('/profile', methods=['GET'])
def profile():
    if 'Id' not in session:
        return redirect('/')
    
    user_id = session['Id']

    conn = get_db()
    cursor = conn.cursor()

    #user info
    cursor.execute("SELECT fName, lName, email, created_at FROM users WHERE Id=%s", (user_id,))
    user = cursor.fetchone()

    #use specific progress
    # cursor.execute("SELECT skill, progress,updated_at FROM progress WHERE user_id = %s", (user_id,))
    cursor.execute("""
   SELECT 
    us.id AS skill_id,
    us.skill_name,
    COALESCE(p.progress, 0) AS progress,
    COALESCE(p.updated_at, us.created_at) AS updated_at
FROM user_skills us
LEFT JOIN progress p 
    ON us.id = p.skill_id AND us.user_id = p.user_id
WHERE us.user_id = %s
ORDER BY us.created_at DESC
""", (user_id,))
    progress_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('profile.html',
                        user={
                'fName': user[0],
                'lName': user[1],
                'email': user[2],
                'created_at': user[3]
            },
    progress_data= progress_data)


@app.route('/add_progress', methods=['POST'])
def add_progress():
    if 'Id' not in session:
        return {"status": "error"}

    user_id = session['Id']
    skill_id = request.form.get('skill_id')
    progress = int(request.form.get('progress')or 0)

    conn = get_db()
    cursor = conn.cursor()


    # check if skill already exists → update
    cursor.execute("SELECT id FROM progress WHERE user_id=%s AND skill_id=%s", (user_id, skill_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
        UPDATE progress SET progress=%s WHERE user_id=%s AND skill_id=%s
        """, (progress, user_id, skill_id))
    else:
        cursor.execute("""
        INSERT INTO progress (user_id, skill_id, progress)
        VALUES (%s, %s, %s)
        """, (user_id, skill_id, progress))

    conn.commit()

    cursor.close()
    conn.close()

    return {"status": "success"}


@app.route('/login_validation', methods=['POST'])
def login_validation():
    email = request.form.get('email')
    password = request.form.get('password')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
    "SELECT Id,fName,role FROM users  WHERE email=%s AND password=%s",
    (email, password)
    )
    
    users = cursor.fetchone()
    cursor.close()
    conn.close()

    if users:
        session['Id'] =users[0]
        session['name'] =users[1]
        session['role'] =users[2]

        if users[2] =="admin":
          return redirect('/admin_dashboard')
        elif users[2] == "company":
          return redirect('/company_dashboard')  
        else:
          return redirect('/dashboard')  

    
    return redirect('/register')
    


@app.route('/add_user', methods=['POST'])
def add_user():
    fName= request.form.get('fName')
    lName = request.form.get('lName')
    email = request.form.get('email')
    password = request.form.get('password')
    role = 'user'

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
                   INSERT INTO users (fName, lName, email, password, role) 
                   VALUES (%s, %s, %s, %s, %s)
                   """, (fName, lName, email, password, role))
    
    
    conn.commit()

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    myuser=cursor.fetchone()

    cursor.close()
    conn.close()

    session['Id'] = myuser[0]
    return redirect('/dashboard')



@app.route('/logout')
def logout():
    session.pop('Id', None)
    return redirect('/')



# Admin
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT fName FROM users WHERE Id=%s", (session['Id'],))
    admin = cursor.fetchone()[0]

    # count ONLY normal users (exclude admin)
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='user'")
    users = cursor.fetchone()[0]

    # UNIQUE QUIZ ATTEMPTS (user + quiz combination)
    cursor.execute("SELECT COUNT(DISTINCT user_id, quiz_id) FROM quiz_results")
    attempts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM quiz_results")
    active_users = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template("admin_dashboard.html", users=users, attempts=attempts, admin_name=admin, active_users=active_users)

@app.route('/create_quiz', methods=['GET','POST'])
def create_quiz():
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    if request.method == 'POST':
        title = request.form.get('title')
        tags_raw = request.form.get('tags', '')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO quizzes (title, created_by)
            VALUES (%s, %s)
        """, (title, session['Id']))

        quiz_id = cursor.lastrowid

        tags = [t.strip().lower() for t in tags_raw.split(',') if t.strip()]
        for tag in tags:
            cursor.execute(
                "INSERT INTO quiz_tags (quiz_id, tag) VALUES (%s, %s)",
                (quiz_id, tag)
            )
 

        conn.commit()
        cursor.close()
        conn.close()


        return redirect(f'/add_question/{quiz_id}')

    return render_template("create_quiz.html")


@app.route('/add_question/<int:quiz_id>', methods=['GET', 'POST'])
def add_question(quiz_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.form

        cursor.execute("""
            INSERT INTO quiz_questions
            (quiz_id, question, option_a, option_b, option_c, option_d, correct_option)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            quiz_id,
            data['question'],
            data['a'],
            data['b'],
            data['c'],
            data['d'],
            data['correct']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(f'/add_question/{quiz_id}')

    cursor.close()
    conn.close()

    return render_template("add_questions.html", quiz_id=quiz_id)



@app.route('/quiz_list')
def quiz_list():
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            q.id,
            q.title,
            q.created_at,
            GROUP_CONCAT(qt.tag ORDER BY qt.tag SEPARATOR ', ') as tags
        FROM quizzes q
        LEFT JOIN quiz_tags qt ON q.id = qt.quiz_id
        GROUP BY q.id, q.title, q.created_at
        ORDER BY q.id DESC
    """)
    quizzes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("Quiz_list.html", quizzes=quizzes)


@app.route('/quizzes')
def quizzes():
    conn = get_db()
    cursor = conn.cursor()

    # cursor.execute("SELECT * FROM quizzes")
    # quizzes = cursor.fetchall()

    cursor.execute("""
    SELECT 
        q.id,
        q.title,
        COUNT(qq.id) AS total_questions
    FROM quizzes q
    LEFT JOIN quiz_questions qq 
        ON q.id = qq.quiz_id
    GROUP BY q.id, q.title
""")

    quizzes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("quizzes.html", quizzes=quizzes)


@app.route('/take_quiz/<int:quiz_id>')
def take_quiz(quiz_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT title FROM quizzes WHERE id=%s", (quiz_id,))
    quiz = cursor.fetchone()

    cursor.execute("SELECT * FROM quiz_questions WHERE quiz_id=%s", (quiz_id,))
    questions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "take_quiz.html",
        quiz_id=quiz_id,
        quiz_title=quiz[0] if quiz else "Quiz",
        questions=questions,
        total_questions=len(questions)
    )


@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):

    if 'Id' not in session:
        return "User not logged in. Please login to take the quiz.", 401
    
    if session.get('role') != 'user':
        return "Only users can submit quiz", 403

    user_id = session['Id']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, correct_option FROM quiz_questions WHERE quiz_id=%s", (quiz_id,))
    questions = cursor.fetchall()

    score = 0
    total = len(questions)

    for q in questions:
        qid = str(q[0])
        if request.form.get(qid) == q[1]:
            score += 1

    cursor.execute("""
        INSERT INTO quiz_results (user_id, quiz_id, score, total)
        VALUES (%s,%s,%s,%s)
    """, (user_id, quiz_id, score, total))

    conn.commit()
    cursor.close()
    conn.close()

    compute_recommendations(user_id)
 
    return redirect(f'/quiz_result/{quiz_id}/{score}/{total}')

    # return f"Score: {score}/{total}"


@app.route('/quiz_result/<int:quiz_id>/<int:score>/<int:total>')
def quiz_result(quiz_id, score, total):
    if 'Id' not in session:
        return redirect('/')
 
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM quizzes WHERE id=%s", (quiz_id,))
    quiz = cursor.fetchone()
    cursor.close()
    conn.close()
 
    pct = round((score / total) * 100) if total > 0 else 0
 
    return render_template('quiz_result.html',
                           quiz_title=quiz[0] if quiz else "Quiz",
                           score=score,
                           total=total,
                           pct=pct)
 
 

@app.route('/view_results')
def view_results():
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT users.fName, quizzes.title, quiz_results.score, quiz_results.total
        FROM quiz_results
        JOIN users ON users.Id = quiz_results.user_id
        JOIN quizzes ON quizzes.id = quiz_results.quiz_id
    """)

    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("view_results.html", results=results)



# Company
@app.route('/company')
def company():
    if 'company_id' in session:
        return redirect('/company_dashboard')
    return render_template("company.html")


@app.route('/company_register', methods=['POST'])
def company_register():
    Cname = request.form.get('Cname')
    Cemail = request.form.get('Cemail')
    password = request.form.get('password')
    website = request.form.get('website')
    location = request.form.get('location')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO company (Cname, Cemail, Password, Website, location)
        VALUES (%s, %s, %s, %s, %s)
    """, (Cname, Cemail, password, website, location))

    conn.commit()

    # login automatically
    cursor.execute("SELECT * FROM company WHERE Cemail=%s", (Cemail,))
    company = cursor.fetchone()

    cursor.close()
    conn.close()
    session['company_id'] = company[0]
    return redirect('/company_dashboard')



@app.route('/company_login', methods=['POST'])
def company_login():
    Cemail = request.form.get('Cemail')
    password = request.form.get('password')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM company WHERE Cemail=%s AND Password=%s",
        (Cemail, password)
    )
    company = cursor.fetchone()
    cursor.close()
    conn.close()
    if company:
        session['company_id'] = company[0]
        return redirect('/company_dashboard')
    else:
        return render_template("company.html", login_error="Invalid credentials")
 


# Company dashboard
@app.route('/company_dashboard')
def company_dashboard():
    if 'company_id' not in session:
        return redirect('/company')
    
    conn= get_db()
    cursor=conn.cursor()

    cursor.execute("SELECT Cname FROM company WHERE Id=%s", (session['company_id'],))
    company = cursor.fetchone()

    cursor.close()
    conn.close()

    if company:
        return render_template("company_dashboard.html", company_name=company[0])
    else:
        session.pop('company_id', None)
        return redirect('/company')
    

    # Logout
@app.route('/company_logout')
def company_logout():
    session.pop('company_id', None)
    return redirect('/company')




@app.route('/post_job')
def post_job():
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, description, location, salary, job_type 
        FROM jobs 
        WHERE company_id=%s
        ORDER BY id DESC
    """, (cid,))

    jobs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('post_job.html', jobs=jobs)



@app.route('/submit_job', methods=['POST'])
def submit_job():
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    title = request.form.get('title')
    description = request.form.get('description')
    location = request.form.get('location')
    salary = request.form.get('salary')
    job_type = request.form.get('job_type')

    # BASIC VALIDATION (don't skip this)
    if not title or not description:
        return "Title and Description required"
    
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobs (company_id, title, description, location, salary, job_type)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (cid, title, description, location, salary, job_type))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/company_dashboard')




# MANAGE JOBS PAGE
@app.route('/manage_jobs')
def manage_jobs():
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    conn = get_db()
    cursor = conn.cursor()

    # Fetch all jobs for this company
    cursor.execute("SELECT id, title, description, job_type, location, salary, created_at FROM jobs WHERE company_id=%s ORDER BY created_at DESC", (cid,))
    jobs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('manage_jobs.html', jobs=jobs)

# DELETE JOB
@app.route('/delete_job/<int:job_id>')
def delete_job(job_id):
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    conn = get_db()
    cursor = conn.cursor()
    
    # Ensure company owns the job
    cursor.execute("DELETE FROM jobs WHERE id=%s AND company_id=%s", (job_id, cid))
    conn.commit()

    cursor.close()
    conn.close()
    
    return redirect('/manage_jobs')

# EDIT JOB PAGE
@app.route('/edit_job/<int:job_id>')
def edit_job(job_id):
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, location, salary, job_type FROM jobs WHERE id=%s AND company_id=%s", (job_id, cid))
    job = cursor.fetchone()

    cursor.close()
    conn.close()

    if not job:
        return "Job not found or unauthorized"

    return render_template('manage_jobs.html', job=job)

# UPDATE JOB (POST)
@app.route('/update_job/<int:job_id>', methods=['POST'])
def update_job(job_id):
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    title = request.form.get('title')
    description = request.form.get('description')
    location = request.form.get('location')
    salary = request.form.get('salary')
    job_type = request.form.get('job_type')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs SET title=%s, description=%s, location=%s, salary=%s, job_type=%s
        WHERE id=%s AND company_id=%s
    """, (title, description, location, salary, job_type, job_id, cid))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/manage_jobs')




# Application
@app.route('/company_applications')
def company_applications():
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            applications.id,
            jobs.title,
            users.fName,
            users.email,
            applications.cover_letter,
            applications.resume,
            applications.status,
            applications.applied_at
        FROM applications
        JOIN jobs ON applications.job_id = jobs.id
        JOIN users ON applications.user_id = users.Id
        WHERE applications.company_id = %s
        ORDER BY applications.applied_at DESC
    """, (cid,))

    applications = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("company_applications.html", applications=applications)


@app.route('/company_applications/<status>')
def filter_applications(status):
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            applications.id,
            jobs.title,
            users.fName,
            users.email,
            applications.status,
            applications.applied_at
        FROM applications
        JOIN jobs ON applications.job_id = jobs.id
        JOIN users ON applications.user_id = users.Id
        WHERE applications.company_id = %s AND applications.status = %s
        ORDER BY applications.applied_at DESC
    """, (cid, status))

    applications = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("company_applications.html", applications=applications)


@app.route('/update_status/<int:app_id>/<status>')
def update_status(app_id, status):
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE applications
        SET status = %s
        WHERE id = %s AND company_id = %s
    """, (status, app_id, cid))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/company_applications')



# Payment
@app.route('/internship_payments')
def internship_payments():
    if 'company_id' not in session:
        return redirect('/company')

    cid = session['company_id']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            p.id,
            u.fName,
            u.email,
            p.amount,
            p.payment_status,
            p.payment_method,
            p.created_at
        FROM internship_payments p
        JOIN users u ON p.user_id = u.Id
        WHERE p.company_id = %s
        ORDER BY p.created_at DESC
    """, (cid,))

    payments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("internship_payments.html", payments=payments)


@app.route('/verify_payment/<int:pid>')
def verify_payment(pid):
    if 'company_id' not in session:
        return redirect('/company')
    
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE internship_payments
        SET payment_status='Active'
        WHERE id=%s
    """, (pid,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/internship_payments')


# MARKET
@app.route('/market')
def market():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT YEAR(posted_date), AVG(salary)
        FROM job_market_data
        GROUP BY YEAR(posted_date)
        ORDER BY YEAR(posted_date)
    """)
    salary_trend = cursor.fetchall()

    cursor.execute("""
       SELECT skill, COUNT(job_id) as demand
       FROM job_skills
       GROUP BY skill
       ORDER BY demand DESC
       LIMIT 5
    """)
    top_skills = cursor.fetchall()

    cursor.execute("""
        SELECT job_role, AVG(salary)
        FROM job_market_data
        GROUP BY job_role
        ORDER BY AVG(salary) DESC
        LIMIT 5
    """)
    top_roles = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM job_market_data")
    total_jobs = cursor.fetchone()[0]


    salary_trend = [(int(y), float(s)) for y, s in salary_trend]
    top_skills = [(str(skill), int(c)) for skill, c in top_skills]
    top_roles = [(str(role), float(s)) for role, s in top_roles]

    cursor.close()
    conn.close()

    return render_template("market.html",
        salary_trend=salary_trend,
        top_skills=top_skills,
        top_roles=top_roles,
        total_jobs=total_jobs
    )
    



# Skillls
@app.route('/skills')
def skills():
    if 'Id' not in session:
        return redirect('/')

    user_id = session['Id']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, skill_name, skill_type, proficiency
        FROM user_skills
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (user_id,))

    # skills = cursor.fetchall()
    skills_raw = cursor.fetchall()

    skills = [
      {
        "id": s[0],
        "name": s[1],
        "type": s[2],
        "proficiency": s[3]
       }
       for s in skills_raw
    ]

    cursor.close()
    conn.close()

    return render_template("skills.html", skills=skills)


@app.route('/add_skill', methods=['POST'])
def add_skill():
    if 'Id' not in session:
        return {"status": "error"}

    user_id = session['Id']
    skill_name = request.form.get('skill_name')
    skill_type = request.form.get('skill_type')
    proficiency = request.form.get('proficiency') or "Intermediate"

    # if not skill_name or len(skill_name.strip()) < 2:
    clean_skill = skill_name.strip()

    if clean_skill == "":
      return {"status": "error", "message": "Please enter a skill name"}

    if len(clean_skill) > 50:
      return {"status": "error", "message": "Skill name too long"}

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM user_skills
        WHERE user_id=%s AND skill_name=%s
    """, (user_id, skill_name.strip()))

    if cursor.fetchone():
        return {"status": "error", "message": "Skill exists"}

    cursor.execute("""
        INSERT INTO user_skills (user_id, skill_name, skill_type, proficiency)
        VALUES (%s,%s,%s,%s)
    """, (user_id, skill_name.strip(), skill_type, proficiency))

    conn.commit()
    skill_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return {"status": "success", "id": skill_id}


@app.route('/delete_skill/<int:skill_id>')
def delete_skill(skill_id):
    if 'Id' not in session:
        return redirect('/')

    user_id = session['Id']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM user_skills
        WHERE id=%s AND user_id=%s
    """, (skill_id, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/skills')



# # RECOMMENDATIon
def compute_recommendations(user_id):
    conn = get_db()
    cursor = conn.cursor()

    # 1. User skills
    cursor.execute("SELECT LOWER(skill_name) FROM user_skills WHERE user_id=%s", (user_id,))
    user_skills = set(row[0] for row in cursor.fetchall())

    # 2. Quiz scores — separate query, separate fetchall, no cursor reuse
    cursor.execute("""
        SELECT quiz_id, MAX(CASE WHEN total > 0 THEN (score * 100.0 / total) ELSE 0 END)
        FROM quiz_results
        WHERE user_id=%s
        GROUP BY quiz_id
    """, (user_id,))
    rows = cursor.fetchall()  # consume immediately into a variable
    quiz_scores = {int(row[0]): float(row[1]) for row in rows}

    # 3. Quiz titles
    cursor.execute("SELECT id, LOWER(title) FROM quizzes")
    quiz_titles = {row[0]: row[1] for row in cursor.fetchall()}

    # 4. Quiz tags
    cursor.execute("SELECT quiz_id, LOWER(tag) FROM quiz_tags")
    quiz_tag_map = {}
    for row in cursor.fetchall():
        quiz_tag_map.setdefault(int(row[0]), set()).add(row[1])

    # 5. User domains
    cursor.execute("SELECT domain_id FROM user_domain_preferences WHERE user_id=%s", (user_id,))
    user_domains = set(int(row[0]) for row in cursor.fetchall())

    # 6. All careers
    cursor.execute("""
        SELECT id, domain_id, required_skills, required_quiz_tags, min_quiz_score_pct
        FROM careers
    """)
    careers = cursor.fetchall()

    results = []

    for career in careers:
        career_id, domain_id, req_skills_str, req_quiz_tags_str, min_quiz_pct = career

        # --- SKILL SCORE (0-50) ---
        req_skills = [s.strip().lower() for s in (req_skills_str or "").split(",") if s.strip()]

        if req_skills and user_skills:
            matched = sum(
                1 for req in req_skills
                if any(req in us or us in req for us in user_skills)
            )
            skill_score = round((matched / len(req_skills)) * 50)
        elif not req_skills:
            skill_score = 25
        else:
            skill_score = 0

        # --- QUIZ SCORE (0-30) ---
        req_tags = [t.strip().lower() for t in (req_quiz_tags_str or "").split(",") if t.strip()]
        quiz_score_contrib = 10  # baseline for users who haven't taken quizzes yet

        if req_tags and quiz_scores:
            relevant_scores = []
            for qid, score_pct in quiz_scores.items():
                title = quiz_titles.get(qid, "")
                tags = quiz_tag_map.get(qid, set())
                is_relevant = any(tag in title or tag in tags for tag in req_tags)
                if is_relevant:
                    relevant_scores.append(score_pct if score_pct >= (min_quiz_pct or 0) else score_pct * 0.5)

            if relevant_scores:
                avg = sum(relevant_scores) / len(relevant_scores)
                quiz_score_contrib = round((avg / 100) * 30)

        # --- DOMAIN SCORE (0 or 20) ---
        domain_score = 20 if (domain_id and int(domain_id) in user_domains) else 0

        total = min(skill_score + quiz_score_contrib + domain_score, 100)

        results.append({
            "career_id": career_id,
            "match_score": total,
            "skill_match_score": skill_score,
            "quiz_match_score": quiz_score_contrib,
            "domain_match_score": domain_score
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    # top = results[:10]
    top = [r for r in results if r["match_score"] >= 60]

    # DELETE then INSERT — use the SAME cursor/connection
    cursor.execute("DELETE FROM recommendations WHERE user_id=%s", (user_id,))

    for r in top:
        cursor.execute("""
            INSERT INTO recommendations
                (user_id, career_id, match_score, skill_match_score, quiz_match_score, domain_match_score)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, r["career_id"], r["match_score"],
              r["skill_match_score"], r["quiz_match_score"], r["domain_match_score"]))

    conn.commit()
    cursor.close()
    conn.close()

    return top


@app.route('/select_domains', methods=['GET', 'POST'])
def select_domains():
    if 'Id' not in session:
        return redirect('/')

    user_id = session['Id']
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        selected = request.form.getlist('domains')
        cursor.execute("DELETE FROM user_domain_preferences WHERE user_id=%s", (user_id,))
        for domain_id in selected:
            cursor.execute(
                "INSERT INTO user_domain_preferences (user_id, domain_id) VALUES (%s, %s)",
                (user_id, int(domain_id))
            )
        conn.commit()
        cursor.close()
        conn.close()
        compute_recommendations(user_id)
        return redirect('/recommend')

    cursor.execute("SELECT id, name, icon, description FROM domains ORDER BY name")
    all_domains = cursor.fetchall()

    cursor.execute("SELECT domain_id FROM user_domain_preferences WHERE user_id=%s", (user_id,))
    selected_ids = set(row[0] for row in cursor.fetchall())

    cursor.close()
    conn.close()
    return render_template('select_domains.html', domains=all_domains, selected_ids=selected_ids)


@app.route('/recommend')
def recommend():
    if 'Id' not in session:
        return redirect('/')

    user_id = session['Id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM user_skills WHERE user_id=%s", (user_id,))
    skill_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_domain_preferences WHERE user_id=%s", (user_id,))
    domain_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE user_id=%s", (user_id,))
    rec_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    # Compute if nothing saved yet
    if rec_count == 0:
        compute_recommendations(user_id)

    # Fresh connection to fetch results
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id, c.title, c.description,
            c.salary_min, c.salary_max, c.growth_potential, c.required_skills,
            d.name,
            r.match_score, r.skill_match_score, r.quiz_match_score, r.domain_match_score
        FROM recommendations r
        JOIN careers c ON r.career_id = c.id
        LEFT JOIN domains d ON c.domain_id = d.id
        WHERE r.user_id = %s
        ORDER BY r.match_score DESC
    """, (user_id,))
    recs = cursor.fetchall()

    cursor.execute("SELECT LOWER(skill_name) FROM user_skills WHERE user_id=%s", (user_id,))
    user_skills = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    recommendations = []
    for row in recs:
        skills_list = [s.strip() for s in (row[6] or "").split(",") if s.strip()][:6]
        recommendations.append({
            "id": row[0], "title": row[1], "description": row[2],
            "salary_min": row[3] or 0, "salary_max": row[4] or 0,
            "growth": row[5] or "Medium", "skills": skills_list,
            "domain": row[7] or "General",
            "match_score": row[8], "skill_score": row[9],
            "quiz_score": row[10], "domain_score": row[11]
        })

    return render_template('recommend.html',
                           recommendations=recommendations,
                           skill_count=skill_count,
                           domain_count=domain_count,
                           user_skills=user_skills)


@app.route('/regenerate_recommendations')
def regenerate_recommendations():
    if 'Id' not in session:
        return redirect('/')

    user_id = session['Id']

    # Explicitly delete first on a dedicated connection
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recommendations WHERE user_id=%s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    # Now recompute fresh
    compute_recommendations(user_id)

    return redirect('/recommend?refreshed=1')


# ---- DEBUG: visit /debug_rec while logged in ----
@app.route('/debug_rec')
def debug_rec():
    if 'Id' not in session:
        return {"error": "not logged in"}

    user_id = session['Id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT LOWER(skill_name) FROM user_skills WHERE user_id=%s", (user_id,))
    skills = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT quiz_id, score, total FROM quiz_results WHERE user_id=%s", (user_id,))
    quizzes = [{"quiz_id": r[0], "score": r[1], "total": r[2]} for r in cursor.fetchall()]

    cursor.execute("SELECT domain_id FROM user_domain_preferences WHERE user_id=%s", (user_id,))
    domains = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM careers")
    career_count = cursor.fetchone()[0]

    cursor.execute("SELECT career_id, match_score FROM recommendations WHERE user_id=%s ORDER BY match_score DESC", (user_id,))
    recs = [{"career_id": r[0], "score": r[1]} for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {
        "user_id": user_id,
        "skills": skills,
        "skill_count": len(skills),
        "quiz_results": quizzes,
        "selected_domain_ids": domains,
        "careers_in_db": career_count,
        "saved_recommendations": recs
    }


@app.route('/tag_quiz/<int:quiz_id>', methods=['GET', 'POST'])
def tag_quiz(quiz_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        tags_raw = request.form.get('tags', '')
        tags = [t.strip().lower() for t in tags_raw.split(',') if t.strip()]
        cursor.execute("DELETE FROM quiz_tags WHERE quiz_id=%s", (quiz_id,))
        for tag in tags:
            cursor.execute("INSERT INTO quiz_tags (quiz_id, tag) VALUES (%s, %s)", (quiz_id, tag))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/quiz_list')

    cursor.execute("SELECT title FROM quizzes WHERE id=%s", (quiz_id,))
    quiz = cursor.fetchone()
    cursor.execute("SELECT tag FROM quiz_tags WHERE quiz_id=%s", (quiz_id,))
    existing_tags = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    return render_template('tag_quiz.html',
                           quiz_id=quiz_id,
                           quiz_title=quiz[0] if quiz else "",
                           existing_tags=", ".join(existing_tags))


# Analyze Skill Gap
@app.route('/skill_gap')
def skill_gap():
    if 'Id' not in session:
        return redirect('/')

    user_id = session['Id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title FROM careers ORDER BY title")
    careers = cursor.fetchall()

    cursor.execute("SELECT skill_name, proficiency FROM user_skills WHERE user_id=%s", (user_id,))
    user_skills = cursor.fetchall()

    cursor.execute("""
        SELECT q.title, MAX(CASE WHEN qr.total > 0 THEN (qr.score * 100.0 / qr.total) ELSE 0 END)
        FROM quiz_results qr
        JOIN quizzes q ON qr.quiz_id = q.id
        WHERE qr.user_id = %s
        GROUP BY q.id, q.title
    """, (user_id,))
    quiz_scores = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('skill_gap.html',
                           careers=careers,
                           user_skills=user_skills,
                           quiz_scores=quiz_scores)


def skills_match(user_skill, required_skill):
    """
    Match user skill against a required skill.
    Both inputs must already be lowercase stripped strings.

    Rules:
    - Exact match always works            : 'sql' == 'sql'       ✓
    - Short skills (<=2 chars)            : exact only, no substr ✓
    - Longer skills                       : word-boundary substr  ✓
    - Case already handled by caller      : both are lowercased   ✓
    """
    us  = user_skill.strip()
    req = required_skill.strip()

    if not us or not req:
        return False

    # Exact match
    if us == req:
        return True

    # Short skills — exact only (prevents 'r' matching 'learning')
    if len(us) <= 2 or len(req) <= 2:
        return False

    # Word-boundary substring match
    if re.search(r'\b' + re.escape(req) + r'\b', us):
        return True
    if re.search(r'\b' + re.escape(us) + r'\b', req):
        return True

    return False


@app.route('/skill_gap_analysis', methods=['POST'])
def skill_gap_analysis():
    if 'Id' not in session:
        return {"error": "not logged in"}, 401

    user_id = session['Id']
    career_id = request.form.get('career_id')

    if not career_id:
        return {"error": "no career selected"}, 400

    conn = get_db()
    cursor = conn.cursor()

    # Target career
    cursor.execute("""
        SELECT title, required_skills, description, salary_min, salary_max, growth_potential
        FROM careers WHERE id=%s
    """, (career_id,))
    career = cursor.fetchone()

    if not career:
        cursor.close()
        conn.close()
        return {"error": "career not found"}, 404

    career_title, req_skills_str, description, sal_min, sal_max, growth = career

    # Parse required skills — strip, lowercase each one
    required_skills = [s.strip().lower() for s in (req_skills_str or "").split(",") if s.strip()]

    # User skills from user_skills table — force lowercase
    cursor.execute("""
        SELECT LOWER(TRIM(skill_name)), proficiency
        FROM user_skills
        WHERE user_id=%s
    """, (user_id,))
    user_skill_map = {}
    for row in cursor.fetchall():
        skill_name = row[0]
        proficiency = row[1]
        user_skill_map[skill_name] = proficiency

    # Quiz scores — also use quiz TITLE as an implicit skill signal
    # e.g. if user scored 60%+ on "SQL" quiz, treat "sql" as a known skill
    cursor.execute("""
        SELECT LOWER(TRIM(q.title)),
               MAX(CASE WHEN qr.total > 0 THEN ROUND(qr.score * 100.0 / qr.total) ELSE 0 END)
        FROM quiz_results qr
        JOIN quizzes q ON qr.quiz_id = q.id
        WHERE qr.user_id = %s
        GROUP BY q.id, q.title
    """, (user_id,))

    quiz_score_map = {}   # lowercase title -> score %
    for row in cursor.fetchall():
        quiz_score_map[row[0]] = float(row[1])

    # Also fetch quiz tags as skill signals
    cursor.execute("""
        SELECT LOWER(TRIM(qt.tag)),
               MAX(CASE WHEN qr.total > 0 THEN ROUND(qr.score * 100.0 / qr.total) ELSE 0 END)
        FROM quiz_results qr
        JOIN quiz_tags qt ON qr.quiz_id = qt.quiz_id
        WHERE qr.user_id = %s
        GROUP BY qt.tag
    """, (user_id,))
    for row in cursor.fetchall():
        tag = row[0]
        score = float(row[1])
        # Merge: keep highest signal
        if tag not in quiz_score_map or quiz_score_map[tag] < score:
            quiz_score_map[tag] = score

    # For display purposes — original quiz title casing and score
    cursor.execute("""
        SELECT q.title, MAX(CASE WHEN qr.total > 0 THEN ROUND(qr.score * 100.0 / qr.total) ELSE 0 END)
        FROM quiz_results qr
        JOIN quizzes q ON qr.quiz_id = q.id
        WHERE qr.user_id = %s
        GROUP BY q.id, q.title
    """, (user_id,))
    quiz_scores_display = {row[0]: float(row[1]) for row in cursor.fetchall()}

    cursor.close()
    conn.close()

    proficiency_weight = {
        "beginner":     0.25,
        "intermediate": 0.6,
        "advanced":     0.85,
        "expert":       1.0
    }

    matched_skills = []
    missing_skills = []
    radar_data     = []

    for req in required_skills:
        matched   = False
        user_prof = None
        weight    = 0

        # 1. Check user_skills table first
        for us, prof in user_skill_map.items():
            if skills_match(us, req):
                matched   = True
                user_prof = prof
                weight    = proficiency_weight.get((prof or "").lower(), 0.25)
                break

        # 2. If not found in skills, check quiz scores as implicit skill evidence
        #    e.g. scored 60%+ on "SQL" quiz → treat as knowing sql at beginner level
        if not matched:
            for quiz_key, score_pct in quiz_score_map.items():
                if skills_match(quiz_key, req) and score_pct >= 50:
                    matched   = True
                    user_prof = "beginner"  # quiz-implied, not explicitly added
                    weight    = (score_pct / 100) * 0.5  # partial credit from quiz
                    break

        radar_data.append({
            "skill":          req,
            "user_level":     round(weight * 100),
            "required_level": 100
        })

        if matched:
            matched_skills.append({
                "name":        req,
                "proficiency": user_prof or "beginner"
            })
        else:
            missing_skills.append(req)

    gap_score = round((len(matched_skills) / len(required_skills)) * 100) if required_skills else 0

    return {
        "career_title":   career_title,
        "description":    description,
        "salary_min":     sal_min or 0,
        "salary_max":     sal_max or 0,
        "growth":         growth or "Medium",
        "gap_score":      gap_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "radar_data":     radar_data[:8],
        "quiz_scores":    quiz_scores_display,
        "total_required": len(required_skills)
    }




if __name__ == "__main__":
    app.run(debug=True)