from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_wtf import FlaskForm
from flask import flash, redirect, url_for, request, render_template
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Email
from datetime import datetime
from flask_apscheduler import APScheduler
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from models import Reminder
from wtforms.validators import DataRequired, Email, Length
from flask_babelex import Babel, _
from models import User

import logging
logging.basicConfig(level=logging.INFO)

import secrets
from extensions import db
import requests  # New import for sending Telegram messages

scheduler = APScheduler()  # This is defining scheduler at the global scope.

# Telegram function and constants
TOKEN = "6424920558:AAGK5eyO3pvObx0lxIIFn642MH2w_P0hge0"
CHAT_ID = "5894076303"

def send_telegram_message(chat_id, token, message):
    base_url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(base_url, params=params)
    response_json = response.json()

    # Log the response from the Telegram API
    app.logger.info(f"Telegram API Response: {response_json}")

    return response_json


babel = Babel()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secrets.token_hex(16)
    app.config['SCHEDULER_API_ENABLED'] = True

    # Babel configurations
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'

    # Database configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialization of extensions
    db.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app)
    login_manager.init_app(app)

# Initialize the scheduler
    scheduler.init_app(app)
    scheduler.start()

    return app

app = create_app()

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@babel.localeselector
def get_locale():
    return session.get('locale', 'en')

class LoginForm(FlaskForm):
    username = StringField(_('Username'), validators=[DataRequired()])
    password = PasswordField(_('Password'), validators=[DataRequired()])
    submit = SubmitField(_('Login'))

class SignupForm(FlaskForm):
    email = StringField(_('Email'), validators=[DataRequired(), Email()])
    username = StringField(_('Username'), validators=[DataRequired()])
    password = PasswordField(_('Password'), validators=[DataRequired()])
    confirm_password = PasswordField(_('Confirm Password'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_('Sign Up'))

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reminders = db.relationship('Reminder', backref='group', lazy=True)

class SettingsForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    telegram_id = StringField('Telegram Username ID', validators=[DataRequired()])
    submit = SubmitField('Save Changes')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash(_('Invalid username or password.'))
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        # Check if the provided username or email already exists
        existing_user_username = User.query.filter_by(username=form.username.data).first()
        existing_user_email = User.query.filter_by(email=form.email.data).first()

        if existing_user_username:
            flash('Username already exists. Please choose another one.', 'error')
            return redirect(url_for('signup'))

        if existing_user_email:
            flash('Email already exists. Please choose another one or login.', 'error')
            return redirect(url_for('signup'))

        # If neither the username nor email exist, create a new user
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html', form=form)


@app.route('/dashboard/', defaults={'group_id': None})
@app.route('/dashboard/<group_id>')
@login_required
def dashboard(group_id):
    groups = Group.query.filter_by(user_id=current_user.id).all()
    if not groups:
        flash('No groups available. Please add a group.', 'warning')
        return redirect(url_for('add_group'))

    if group_id:
        group = Group.query.filter_by(id=group_id, user_id=current_user.id).first()
    else:
        group = groups[0]

    reminders = Reminder.query.filter_by(group_id=group.id).all()
    return render_template('dashboard.html', current_group=group, groups=groups, reminders=reminders)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/remove_group/<group_id>', methods=['POST'])
@login_required
def remove_group(group_id):
    group = Group.query.get(group_id)
    if group:
        # Delete reminders associated with the group
        Reminder.query.filter_by(group_id=group.id).delete()
        db.session.delete(group)
        db.session.commit()
        flash('Group removed successfully!', 'success')
    else:
        flash('Error removing group.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/add_group')
@login_required
def add_group():
    groups = Group.query.filter_by(user_id=current_user.id).all()
    new_group_name = f"Group {str(len(groups) + 1)}"
    new_group = Group(name=new_group_name, user_id=current_user.id)
    
    try:
        db.session.add(new_group)
        db.session.commit()
        flash('Group added successfully!', 'success')
    except:
        db.session.rollback()
        flash('Error adding group.', 'error')

    return redirect(url_for('dashboard', group_id=new_group.id))

@app.route('/edit_reminder/<int:reminder_id>', methods=['GET', 'POST'])
@login_required
def edit_reminder(reminder_id):
    reminder = Reminder.query.get(reminder_id)
    if not reminder:
        flash('Reminder not found!', 'error')
        return redirect(url_for('dashboard'))

    # If it's a POST request (form submission), process the updated data
    if request.method == 'POST':
        # Extract data from the form
        reminder_text = request.form.get('reminder_text')
        reminder_datetime_str = request.form.get('reminder_datetime')
        reminder_datetime_obj = datetime.fromisoformat(reminder_datetime_str)
        notification_method = request.form.get('notification_method')

        # Update reminder attributes
        reminder.text = reminder_text
        reminder.date_time = reminder_datetime_obj
        reminder.notification_method = notification_method

        # Save changes to the database
        try:
            db.session.commit()
            flash('Reminder updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating reminder: {e}', 'error')

        # Redirect back to the dashboard
        return redirect(url_for('dashboard'))

    return render_template('edit_reminder.html', reminder=reminder)

@app.route('/create_reminder_for_group/<group_id>', methods=['POST'])
@login_required
def create_reminder_for_group(group_id):
    if request.method == 'POST':
        # Extract data from form
        reminder_text = request.form.get('reminder_text')
        
        # Convert string to datetime object
        reminder_datetime_str = request.form.get('reminder_datetime')
        reminder_datetime_obj = datetime.fromisoformat(reminder_datetime_str)

        notification_method = request.form.get('notification_method')

        # Ensure the reminder date is in the future (simple check)
        if reminder_datetime_obj <= datetime.now():
            flash('Reminder date should be in the future!', 'warning')
            return redirect(url_for('dashboard', group_id=group_id))

        new_reminder = Reminder(text=reminder_text, date_time=reminder_datetime_obj, 
                                notification_method=notification_method, group_id=group_id, user_id=current_user.id)

        try:
            db.session.add(new_reminder)
            db.session.commit()
            flash('Reminder added successfully!', 'success')
        except Exception as e: 
            db.session.rollback()
            flash(f'Error adding reminder: {e}', 'error')

        return redirect(url_for('dashboard', group_id=group_id))
    
    return render_template('create_reminder.html')
    
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm()
    if form.validate_on_submit():
        current_user.phone_number = form.phone_number.data
        current_user.telegram_id = form.telegram_id.data
        # Save changes to the database
        db.session.commit()
        flash('Settings updated!', 'success')
        return redirect(url_for('dashboard'))
    elif request.method == 'GET':
        form.email.data = current_user.email
        form.phone_number.data = current_user.phone_number
        form.telegram_id.data = current_user.telegram_id
    return render_template('settings.html', form=form)

from datetime import datetime


@scheduler.task('interval', id='check_reminders', seconds=60, misfire_grace_time=900)
def check_for_reminders():
    with app.app_context():
        current_datetime = datetime.now()

        # Logging current datetime
        app.logger.info(f"Checking for reminders at: {current_datetime}")

        reminders_to_trigger = Reminder.query.filter(Reminder.date_time <= current_datetime).all()

        # Logging number of reminders fetched
        app.logger.info(f"Number of reminders fetched: {len(reminders_to_trigger)}")

        for reminder in reminders_to_trigger:
            app.logger.info(f"Processing reminder: {reminder.text}, Notification method: {reminder.notification_method}")
            
            if reminder.notification_method.lower() == 'telegram':
                app.logger.info(f"Attempting to send reminder via Telegram: {reminder.text}")
                send_telegram_message(CHAT_ID, TOKEN, f"Reminder: {reminder.text}")

            db.session.delete(reminder)
            
        db.session.commit()


@app.route('/set_language/<language>')
def set_language(language=None):
    session['locale'] = language
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
