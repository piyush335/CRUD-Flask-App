from flask import Flask, render_template, url_for, flash, redirect, session, logging, request
import mysql.connector
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="",
    database="myflaskapp"
)

# Index
@app.route('/')
def index():
    return render_template('home.html')

# About
@app.route('/about')
def about():
    return render_template('about.html')

# Articles
@app.route('/articles')
def articles():
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM articles")
    result = mycursor.fetchall()
    if result:
        return render_template('articles.html', articles=result)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)
    mycursor.close()

#Single Article
@app.route('/find_article/<string:id>/')
def find_article(id):
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM articles WHERE id = %s", [id])
    result = mycursor.fetchone()
    return render_template('find_article.html', article=result)
    mycursor.close()

# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [validators.DataRequired(),validators.EqualTo('confirm', message='Passwords do not match')])
    confirm = PasswordField('Confirm Password')

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        mycursor = mydb.cursor()
        mycursor.execute("INSERT INTO users (name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))
        mydb.commit()
        mycursor.close()

        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        mycursor = mydb.cursor(dictionary=True)
        mycursor.execute("SELECT * FROM users WHERE username = %s", [username])
        result = mycursor.fetchone()
        if result:
            password = result['password']
            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            mycursor.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM articles WHERE author = %s", [session['username']])
    result = mycursor.fetchall()
    if result:
        return render_template('dashboard.html', articles=result)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
    mycursor.close()

# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])

# Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        mycursor = mydb.cursor()
        mycursor.execute("INSERT INTO articles (title, body, author) VALUES (%s, %s, %s)",(title, body, session['username']))
        mydb.commit()
        mycursor.close()

        flash('Article Created', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

# Edit Article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM articles WHERE id = %s", [id])
    result = mycursor.fetchone()
    mycursor.close()

    form = ArticleForm(request.form)
    form.title.data = result['title']
    form.body.data = result['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        mycursor = mydb.cursor()
        app.logger.info(title)
        mycursor.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s",(title, body, id))
        mydb.commit()
        mycursor.close()

        flash('Article Updated', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

# Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    mycursor = mydb.cursor()
    mycursor.execute("DELETE FROM articles WHERE id = %s", [id])
    mydb.commit()
    mycursor.close()

    flash('Article Deleted', 'success')
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    app.secret_key = '0b579d376dc5dde856e0a0ddca6f403cc8707924ff8d6d31'
    app.run(debug=True)