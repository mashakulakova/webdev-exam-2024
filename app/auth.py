from flask import render_template, request, redirect, url_for, flash, Blueprint
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from app import db
from check_user import CheckUser
from functools import wraps

bp_auth = Blueprint('auth', __name__, url_prefix='/auth')

ADMIN_ROLE_ID = 1
MODER_ROLE_ID = 2

def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для доступа необходимо пройти аутентификацию'
    login_manager.login_message_category = 'warning'
    login_manager.user_loader(load_user)
    login_manager.init_app(app)


def check_rights(action):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = None
            if kwargs.get('user_id'):
                user_id = kwargs['user_id']
                user = load_user(user_id)
            if current_user.can(action, user):
                return func(*args, **kwargs)
            else:
                flash("У Вас нет прав.", "danger")
                return redirect(url_for('index'))
        return wrapper
    return decorator


class User(UserMixin):
    def __init__(self, user_id, user_login, role_id):
        self.id = user_id
        self.login = user_login
        self.role_id = role_id
    def is_admin(self):
        return self.role_id == ADMIN_ROLE_ID
    def is_moderator(self):
        return self.role_id == MODER_ROLE_ID   
    def can(self, action):
        if self.role_id:
            if action == 'create':
                return self.is_admin()
            elif action == 'edit':
                return self.is_admin() or self.is_moderator()
            elif action == 'delete':
                return self.is_admin()
            elif action == 'show':
                return True
        return False
    @property
    def fio(self): 
        return f'{self.last_name} {self.first_name} {self.middle_name or ""}'


def load_user(user_id):
    query = 'SELECT * FROM users WHERE users.id=%s'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(user.id, user.login, user.role_id)
    return None

@bp_auth.route('/login', methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        check = request.form.get('secretcheck') == 'on'
        query = 'SELECT * FROM users WHERE users.login=%s AND users.password_hash=SHA2(%s,256)'
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (login, password))
        user = cursor.fetchone()
        cursor.close()
        if user:
            login_user(User(user.id, user.login, user.role_id), remember=check)
            param_url = request.args.get('next')
            flash('Вы успешно вошли!', 'success')
            return redirect(param_url or url_for('index'))
        flash('Ошибка входа!', 'danger')
    return render_template('login.html' )

@bp_auth.route('/logout', methods = ['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))