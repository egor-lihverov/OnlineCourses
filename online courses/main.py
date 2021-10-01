import io
from collections import defaultdict
from os import path
import socketio
from flask_socketio import emit
from requests import post
import logging
import json
import os

from flask import Flask, request, render_template, send_file, send_from_directory, url_for
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from flask_wtf import FlaskForm
from werkzeug.utils import redirect, secure_filename
from wtforms import (PasswordField, SubmitField, BooleanField, StringField, SelectMultipleField,
                     widgets, IntegerField, SelectField)
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired

from data import db_session
from data.users import User
from data.courses import Course

sio = socketio.Server(async_mode='threading')
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)
app.config['UPLOAD_FOLDER'] = "C:/Users/Egor/Desktop/Онлайн Курсы/courses"
app.config['SECRET_KEY'] = 'secret_key'

logging.basicConfig(level=logging.INFO, format='%(filename)s --> %(levelname)s: %(message)s')

sessionStorage = defaultdict(lambda: None)

login_manager = LoginManager()
login_manager.init_app(app)

if not os.access('./db', os.F_OK):
    os.mkdir('./db')
db_session.global_init('db/online_courses.db')


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route("/", methods=["GET"])
def start_page():
    return render_template('index.html', text=open("text.txt").readlines())


@app.route("/courses", methods=["GET"])
def courses_list():
    session = db_session.create_session()
    courses = session.query(Course).all()
    name = 'None'
    return render_template('courses.html', courses=courses)


@app.route("/course/<int:course_id>")
def show_course(course_id):
    session = db_session.create_session()
    course = session.query(Course).filter(Course.id == course_id).first()
    if course:
        files = []
        if current_user.is_authenticated and str(course.id) in current_user.courses:
            files = os.listdir(f'courses/{course.id}')
            print(files)
            for i in range(len(files)):
                if files[i] == 'description.txt':
                    del(files[i])
                    break

        # with io. open(f"courses/{course.id}/description.txt", 'r') as f:
        #     contents = f.read()
        # contents = contents.rstrip("\n").decode("utf-16")
        # contents = contents.split("\r\n")

        return render_template('course_2.html', course=course, course_id=str(course.id), description=open(f"courses/{course.id}/description.txt"), files=files)


@app.route("/login", methods=["GET", "POST"])
def login():
    session = db_session.create_session()
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        print(email)
        print(password)
        user = session.query(User).filter(User.email == email).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect("/")
        return render_template('login.html', message='Ошибка при вводе данных')
    else:
        return render_template('login.html', message='')


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password2']
        name = request.form['name']
        print(email)
        print(password)
        print(password2)
        if password != password2:
            return render_template('register.html', message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(User).filter(User.email == email).first():
            return render_template('register.html', message="Такой пользователь уже есть")
        user = User(email=email, name=name, status=0)
        user.set_password(password)
        session.add(user)
        session.commit()

        return redirect("/login")
    else:
        return render_template('register.html', message='')


@app.route('/join_course/<int:course_id>')
@login_required
def join_course(course_id):
    session = db_session.create_session()
    course = session.query(Course).filter(Course.id == course_id).first()
    if course:
        print(current_user.id)
        user = session.query(User).filter(User.id == current_user.id).first()
        print(user.courses)
        user.courses += str(course_id) + " "
        session.commit()
    return redirect(f'/course/{course_id}')


@app.route('/leave_course/<int:course_id>')
@login_required
def leave_course(course_id):
    session = db_session.create_session()
    course = session.query(Course).filter(Course.id == course_id).first()
    if course:
        print(current_user.id)
        user = session.query(User).filter(User.id == current_user.id).first()
        print(user.courses)
        if str(course_id) in user.courses:
            user.courses = user.courses.replace(f'{course_id}', '').replace('  ', ' ')
        session.commit()
        print(user.courses)
    return redirect(f'/course/{course_id}')


@app.route('/create_course', methods=["POST", "GET"])
def create_course():
    if not current_user.is_authenticated or current_user.status != 1:
        return redirect('/courses')
    if request.method == "POST":
        title = request.form['title']
        description = request.form['description']
        duration = request.form['duration']
        files = request.files.getlist('text_files')

        session = db_session.create_session()
        course = Course(title=title, duration=duration, creator=current_user.id)
        session.add(course)
        session.commit()
        courses = session.query(Course).all()
        course = courses[len(courses) - 1]
        print(files)
        os.mkdir(f"courses/{course.id}")
        for file in files:
            filename = secure_filename(file.filename)
            file.save(f'courses/{course.id}/{filename}')
        file = open(f"courses/{course.id}/description.txt", "w")
        file.write(description)
        file.close()
        return redirect('/courses')
    return render_template('course_form.html')


@app.route('/upload', methods=["POST", "GET"])
def upload_file():
    if request.method == "POST":
        file = request.files["text_files"]
        print(file)
        return redirect('/courses')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/download/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    directory = path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    print(directory)
    return send_from_directory(directory=directory, filename=filename)


if __name__ == '__main__':
    app.run()

# <a href="http://127.0.0.1:5000/download/{{ course_id }}/{{file}}" download="">Теория</a>

# {% for file in files %}
#             <a href="/send_file/{{ course_id }}/{{file}}" download>Теория</a>
#             {% endfor %}
