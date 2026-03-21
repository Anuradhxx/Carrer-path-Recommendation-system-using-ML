from flask import Flask, render_template,request,redirect,session
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

conn=mysql.connector.connect(
    host="localhost",
    user="root",          
    password="",  
    database="login"
)

cursor = conn.cursor()

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
        cursor.execute("SELECT fName FROM users WHERE Id=%s", (session['Id'],))
        user = cursor.fetchone()
        return render_template('dashboard.html', user={'fName': user[0]})
    else:
        return redirect('/register')



@app.route('/login_validation', methods=['POST'])
def login_validation():
    email = request.form.get('email')
    password = request.form.get('password')


    cursor.execute(
    "SELECT * FROM users  WHERE email=%s AND password=%s",
    (email, password)
    )
    
    users = cursor.fetchall()
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

    cursor.execute(""" INSERT INTO  `users` (`Id` , `fName`, `lName`, `email`, `password`, `role`) VALUES 
                  (NULL, '{}', '{}', '{}', '{}', '{}') """. format(fName, lName, email, password,role))
    
    conn.commit()

    cursor.execute("""SELECT * FROM `users` WHERE `email` LIKE '{}'""".format(email))
    myuser=cursor.fetchall()
    session['Id'] = myuser[0][0]
    return redirect('/dashboard')



@app.route('/logout')
def logout():
    session.pop('Id', None)
    return redirect('/')





if __name__ == "__main__":
    app.run(debug=True)