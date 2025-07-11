from flask import Flask,render_template,jsonify,request,redirect,url_for,session,flash
import pickle
import pandas as pd
import numpy as np
from flask_mysqldb import MySQL
from dotenv import load_dotenv
import os
load_dotenv()

model_path = "asset_life.pkl"
with open(model_path,'rb') as file:
    model = pickle.load(file)

app= Flask(__name__)
app.secret_key = "SanathWonder2466"

# MySQL configuration
app.config['MYSQL_HOST'] = os.getenv('DB_HOST')
app.config['MYSQL_USER'] = os.getenv('DB_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('DB_NAME')

mysql = MySQL(app)
@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone_number')
        username = request.form.get('username')
        password = request.form.get('password')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s",(username,))
        user = cur.fetchone()
        if user:
            flash("User Already Exists!.Choose Another One") 
            return render_template("signup.html")  
        cur.execute("INSERT INTO users(full_name,phone,username,password) VALUES(%s,%s,%s,%s)",
                    (full_name,phone,username,password))
        mysql.connection.commit()
        cur.close()
        flash("Signup Successful.Please login")
        return redirect(url_for('login'))
    return render_template('signup.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))

        user = cur.fetchone()
        cur.close()
        # dummy db for username and password
        if user:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    return render_template('login.html')
# Route for main prediction page
@app.route('/')
def home():
    if "username" in session:
        return render_template('index.html')
    return redirect(url_for('login'))         
@app.route('/predict',methods=['POST'])
def predic():
    if not "username" in session:
        return redirect(url_for('login'))
    feature_names = [
    'asset_age_years',
    'total_usage_hours',
    'num_repairs',
    'last_maintenance_gap_days',
    'performance_score'
]
    values = [float(x) for x in request.form.values()]
    input_df = pd.DataFrame([values],columns=feature_names)

    # make prediction 
    prediction = model.predict(input_df)
    prediction_value = round(prediction[0],2)
    
    print("features",feature_names)
    print("model prediction",prediction_value)
    return render_template('index.html',prediction_text="prediction_value:{}".format(prediction_value))
#Route to logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
if __name__ == "__main__":
    app.run(debug=True)
        
 