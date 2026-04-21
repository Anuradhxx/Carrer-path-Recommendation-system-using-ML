from flask import Flask, render_template, request, redirect, session
import mysql.connector
import os


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

        cursor.execute("SELECT COUNT(*) FROM quizzes")
        quiz_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return render_template('dashboard.html', user={'fName': user[0]}, quiz_count=quiz_count)
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

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO quizzes (title, created_by)
            VALUES (%s, %s)
        """, (title, session['Id']))

        quiz_id = cursor.lastrowid
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
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM quizzes")
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

    return f"Score: {score}/{total}"

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




if __name__ == "__main__":
    app.run(debug=True)