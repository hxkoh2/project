# all the imports
import os
import uuid
from flask import Flask, request, session, g, redirect, url_for, \
	 abort, render_template, flash
from contextlib import closing
from sqlite3 import dbapi2 as sqlite3
import datetime
from user import User
import json
from flask.ext.login import *


# configuration
#DATABASE = os.path.join(app.root_path, 'flaskr.db')
DATABASE = '/tmp/flaskr.db'
DEBUG = True # leave disabled in production code
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'


# create our little application :)
login_manager = LoginManager()
app = Flask(__name__)
app.config.from_object(__name__)
login_manager.init_app(app)


# connect to our db above
def connect_db():
	return sqlite3.connect(app.config['DATABASE'])


def init_db():
	with closing(connect_db()) as db:
		with app.open_resource('schema.sql', mode='r') as f:
			db.cursor().executescript(f.read())
		db.commit()


@app.before_request
def before_request():
	g.db = connect_db()
	g.db.executescript('PRAGMA foreign_keys=ON')


@app.teardown_request
def teardown_request(exception):
	db = getattr(g, 'db', None)
	if db is not None:
		db.close()


@login_manager.user_loader
def load_user(userid):
	cur = g.db.execute('select type from Person where username = (?)', [userid])
	person = [dict(type=row[0]) for row in cur.fetchall()]
	if len(person) == 0:
		return None
	else:
		return User(userid, person[0]['type'])


def formatDate(d):
	monthDict={1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
	li = d.split('-')
	return '{0} {1}, {2}'.format(monthDict[int(li[1])], li[2], li[0])

def formatTime(t):
	li = t.split(':')
	meridiem = {0:'am', 1:'pm'}
	return  '{0}:{1} {2}'.format( int(li[0])%12,li[1],meridiem[int(li[0])/12])	



##############################Professor Code########################################
@app.route('/temp')
def temp():
	return render_template('temp.html')

@app.route('/add_temp', methods=['POST'])
def add_temp():
	username = request.form['username']
	password = request.form['password']
	student_prof = request.form['student_prof']
	cur = g.db.execute('insert into Person(type, username, password) values (?,?,?)', [student_prof, username, password])
	g.db.commit()
	flash('Person added')
	return redirect(url_for('temp'))

@app.route('/signup')
def signup():
	return render_template('signup.html')

@app.route('/add_user', methods=['POST'])
def add_user():
	type = request.form['type'].lower().strip()
	if type == 'student': type = 0
	else: type = 1

	username = request.form['username']
	password = request.form['password']
	email = request.form['email']

	# check if username already used
	#cur = g.db.execute('select username from Person where username = (?)', [username])
	#user = [dict(class_name=row[0]) for row in cur.fetchall()]
	#if len(user) == 0:
	try:
		cur = g.db.execute('insert into Person(type, username, password, email) values (?,?,?,?)', [type, username, password, email])
		g.db.commit()
		flash('Account created - you may login')
		return redirect(url_for('login'))
	except:
		flash('Error: Username already exists - select new username')
		return redirect(url_for('signup'))

@app.route('/logout')
def logout():
	from flask.ext.login import logout_user
	logout_user()
	return redirect(url_for('login'))

@app.route('/login')
def login():
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return render_template('login.html')
	else:
		if current_user.isStudent:
			return redirect(url_for('student'))
		else:
			return redirect(url_for('professor'))


@app.route('/submit_login', methods=['POST'])
def submit_login():
	username = request.form['username']
	password = request.form['password']
	cur = g.db.execute('select type from Person where username = (?) and password = (?)', [username, password])
	person = [dict(type=row[0]) for row in cur.fetchall()]
	if len(person) == 0:
		flash('Incorrect username or password')
		return redirect(url_for('login'))
	user = User(username, person[0]['type'])
	from flask.ext.login import login_user
	login_user(user)
	if person[0]['type'] == 0:
		return redirect(url_for('student'))
	else:
		return redirect(url_for('professor'))

@app.route('/professor')
def professor():
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return redirect(url_for('login'))
	
	if current_user.isStudent: return redirect(url_for('student'))
	username = current_user.username
	cur = g.db.execute('select * from Class, Subscribes where Class.class_name = Subscribes.class_name AND Subscribes.username="'+username+'"')
	prof_class = [dict(class_name=row[0], class_key=row[1], class_admin=row[2]) for row in cur.fetchall()]
	return render_template('professor.html', classes=prof_class)


@app.route('/professor_class/<username>/<class_name1>')
def professor_class(username, class_name1):
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return redirect(url_for('login'))
	
	if current_user.isStudent: return redirect(url_for('student'))
	cur = g.db.execute('select question_text, question_date, question_time,question_confusion from Question where question_id IN (select question_id from Asked_in where class_name="'+class_name1+'")  order by question_date desc, question_time desc')
	questions = [dict(text=row[0], date=row[1], time=row[2], confusion=row[3]) for row in cur.fetchall()]
	prof_username = current_user.username
	return render_template('class.html', questions=questions, class_name=class_name1)


@app.route('/add_class', methods=['POST'])
def add_class():
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return redirect(url_for('login'))
	
	if current_user.isStudent: return redirect(url_for('student'))
	username = current_user.username
	class_name = request.form['class_name']
	class_key = request.form['class_key']
	class_admins = request.form['class_admins']
	if len(class_name) == 0:
		flash('No class name received. Class not added')
		return redirect(url_for('professor'))
	if len(class_key) == 0:
		flash('No class key received. Class not added')
		return redirect(url_for('professor'))
	if len(class_admins) == 0:
		flash('No admins received. Class not added')
		return redirect(url_for('professor'))
	for admin in class_admins.split(','):
		person = g.db.execute('select username from Person where username="' + admin.strip() + '"').fetchall()
		if len(person) == 0:
			return json.dumps({'status':'incorrect', 'flash':'One of the admins does not exist. Class not added.'})
	try:
		g.db.execute('insert into Class (class_name, class_key, class_admin) values (?, ?, ?)', [class_name, class_key, class_admins])
		g.db.execute('insert into Subscribes (username, class_name) values (?, ?)', [username, class_name])
		g.db.commit()
		return json.dumps({'status':'OK', 'flash':'New class added', 'class_name':class_name, 'class_key':class_key, 'class_admin':class_admins})
	except:
		return json.dumps({'status':'exists', 'flash':'This class already exists'})


@app.route('/delete_class', methods=['POST'])
def delete_class():
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return redirect(url_for('login'))
	
	if current_user.isStudent: return redirect(url_for('student'))
	class_name = request.form['class_name']
	cur = g.db.execute('Select class_admin from Class where class_name="' + class_name + '"')
	class_admins = cur.fetchall()[0][0]
	admins = [admin.strip() for admin in class_admins.split(',')]
	if current_user.username not in admins:
		return json.dumps({'status':'OK', 'flash':'You must be an admin to delete this class'})
	g.db.execute('Delete from Class where class_name = (?)', [class_name])
	g.db.execute('Delete from Subscribes where class_name = (?)', [class_name])
	g.db.commit()
	return json.dumps({'status':'deleted', 'flash':'Class deleted'})


@app.route('/subscribe', methods=['POST'])
def subscribe():
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return redirect(url_for('login'))
	
	if current_user.isStudent: return redirect(url_for('student'))
	class_name = request.form['class_name']
	class_key = request.form['class_key']
	username = current_user.username
	if len(class_name) == 0:
		return json.dumps({'status':'no_class', 'flash':'No class name received and not subscribed'})
	if len(class_key) == 0:
		return json.dumps({'status':'no_key', 'flash':'No class key received and not subscribed'})
	cur = g.db.execute('select * from Class where class_name ="' + class_name + '"')
	classes = cur.fetchall()
	if len(classes) == 0:
		return json.dumps({'status':'not_exist', 'flash':'This class does not exist'})
	if class_key != classes[0][1]:
		return json.dumps({'status':'wrong_key', 'flash':'The key entered is not correct'})
	g.db.execute('insert into Subscribes (username, class_name) values (?, ?)',[username, class_name])
	g.db.commit()
	cur = g.db.execute('Select class_admin from Class where class_name="' + class_name + '"')
	class_admin = cur.fetchall()[0][0]
	return json.dumps({'status':'OK', 'flash':'Subcribed to class', 'class_name':class_name, 'class_key':class_key, 'class_admin':class_admin})

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return redirect(url_for('login'))

	if current_user.isStudent: return redirect(url_for('student'))
	class_name = request.form['class_name']
	print class_name
	username = current_user.username
	cur = g.db.execute('select * from Class where class_name ="' + class_name + '"')
	if len(cur.fetchall()) == 0:
		flash('This class does not exist')
		return redirect(url_for('professor'))
	g.db.execute('Delete from Subscribes where Subscribes.username="' + username + '" AND Subscribes.class_name="' + class_name + '"')
	g.db.commit()
	#flash('Unsubscribed from class')
	#return redirect(url_for('professor'))
	return json.dumps({'status':'OK', 'flash':'Unsubscribed from class'})

@app.route('/update_key', methods=['POST'])
def update_key():
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return redirect(url_for('login'))
	
	if current_user.isStudent: return redirect(url_for('student'))
	newkey = request.form['newkey']
	oldkey = request.form['oldkey']
	if len(newkey) == 0:
		return json.dumps({'status':'OK', 'class_key':oldkey, 'flash':'No key received'})
	class_name = request.form['class_name']
	print class_name
	cur = g.db.execute('Select class_admin from Class where class_name="' + class_name + '"')
	class_admins = cur.fetchall()[0][0]
	admins = [admin.strip() for admin in class_admins.split(',')]
	if current_user.username not in admins:
		return json.dumps({'status':'OK', 'class_key':oldkey, 'flash':'You must be an admin to change the key'})
	g.db.execute('Update Class Set class_key="' + newkey + '" where class_name="' + class_name + '"')
	g.db.commit()
	return json.dumps({'status':'OK', 'class_key':newkey, 'flash':'Key updated'})

@app.route('/update_admin', methods=['POST'])
def update_admin():
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return redirect(url_for('login'))
	
	if current_user.isStudent: return redirect(url_for('student'))
	newadmins = request.form['newadmins']
	class_name = request.form['class_name']
	oldadmins = request.form['oldadmin']
	if len(newadmins) == 0:
		return json.dumps({'status':'OK', 'admin':oldadmins, 'flash':'No admins received'})
	old_admins = [admin.strip() for admin in oldadmins.split(',')]
	if current_user.username not in old_admins:
		return json.dumps({'status':'OK', 'admin':oldadmins, 'flash':'You must be an admin to change the admins'})
	for admin in newadmins.split(','):
		person = g.db.execute('select username from Person where username="' + admin.strip() + '"').fetchall()
		if len(person) == 0:
			return json.dumps({'status':'OK', 'admin':oldadmins, 'flash':'One of the admins does not exist'})
	g.db.execute('Update Class Set class_admin="' + newadmins + '" where class_name="' + class_name + '"')	
	g.db.commit()
	return json.dumps({'status':'OK', 'admin':newadmins, 'flash':'Admins updated'})

##############################Student Code#####################################	
	
@app.route('/student')
def student():
	from flask.ext.login import current_user
	if not current_user.is_authenticated():
		return redirect(url_for('login'))
	if current_user.isProfessor: return redirect(url_for('professor'))
	username = current_user.username
	cur = g.db.execute('select question_text, question_date, question_time, question_confusion from Question where Question.question_id IN (select question_id from Asked_in) order by question_date desc, question_time desc')
	questions = [dict(text=row[0], date=formatDate(row[1]), time=formatTime(row[2]), confusion=row[3]) for row in cur.fetchall()]
	return render_template('student.html', questions=questions)


@app.route('/add_question', methods=['POST'])
def add_question():
	txt = request.form['question']
	class_name1 = request.form['class_name']
	confusion = request.form['confusion']
	username = request.form['username']
	if len(txt) == 0:
		flash('Empty question received and not inserted into db')
		return redirect(url_for('student'))
	dt = datetime.datetime.now()
	date = str(dt.date())
	time = str(dt.time())
	g.db.execute('insert into Question (question_text, question_date, question_time, question_confusion) values (?, ?, ?,?)', [txt, date, time,confusion])
	cur = g.db.execute('select question_id from Question order by question_id desc limit 1')
	qid = cur.fetchall()[0][0]
	g.db.execute('insert into Asks (question_id, username) values(?,?)',[qid, username])
	try:
		g.db.execute('insert into Asked_in (question_id, class_name) values (?, ?)',[qid, class_name1])	
		flash('New question added to class')
	except:
		flash('Class does not exist. Question not added.')
	g.db.commit()
	return redirect(url_for('student'))


if __name__ == '__main__':
	app.run()

