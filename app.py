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
def login():
    return render_template('index.html')

@app.route('/register')
def register():
    return render_template('index.html')


@app.route('/home')
def home():
    if 'Id' in session:
        return render_template('home.html')
    else:
        return redirect('/')

@app.route('/login_validation', methods=['POST'])
def login_validation():
    email = request.form.get('email')
    password = request.form.get('password')


    cursor.execute(""" SELECT * FROM `users`  WHERE `email` LIKE '{}' AND `password` LIKE '{}'"""
                   .format(email, password))
    users = cursor.fetchall()
    if len(users)>0:
        session['Id'] = users[0][0]
        return redirect('/home')
    else:
        return redirect('/')
    


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
    return redirect('/home')



@app.route('/logout')
def logout():
    session.pop('Id')
    return redirect('/')





if __name__ == "__main__":
    app.run(debug=True)