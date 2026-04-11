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
        database="smart_career_database"
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
        cursor.close()
        conn.close()
        return render_template('dashboard.html', user={'fName': user[0]})
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
    cursor.execute("SELECT skill, progress,updated_at FROM progress WHERE user_id = %s", (user_id,))
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
    skill = request.form.get('skill')
    progress = int(request.form.get('progress')or 0)

    conn = get_db()
    cursor = conn.cursor()


    # check if skill already exists → update
    cursor.execute("SELECT * FROM progress WHERE user_id=%s AND skill=%s", (user_id, skill))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
        UPDATE progress SET progress=%s WHERE user_id=%s AND skill=%s
        """, (progress, user_id, skill))
    else:
        cursor.execute("""
        INSERT INTO progress (user_id, skill, progress)
        VALUES (%s, %s, %s)
        """, (user_id, skill, progress))

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
    "SELECT * FROM users  WHERE email=%s AND password=%s",
    (email, password)
    )
    
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    if len(users)>0:
        session['Id'] = users[0][0]
        return redirect('/dashboard')
    else:
        return redirect('/register')
    


@app.route('/add_user', methods=['POST'])
def add_user():
    fName= request.form.get('fName')
    lName = request.form.get('lName')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

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

    session['Id'] = myuser[0][0]
    return redirect('/dashboard')



@app.route('/logout')
def logout():
    session.pop('Id', None)
    return redirect('/')



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









if __name__ == "__main__":
    app.run(debug=True)