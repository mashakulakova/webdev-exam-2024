from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from mysql_db import MySQL
import mysql.connector
import math

app = Flask(__name__)

application = app

app.config.from_pyfile('config.py')

db = MySQL(app)

from auth import bp_auth, check_rights, init_login_manager

app.register_blueprint(bp_auth)

app.jinja_env.globals.update(current_user=current_user)

init_login_manager(app)

PER_PAGE = 6

def get_genres():
    query = 'SELECT * FROM genres'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    roles = cursor.fetchall()
    cursor.close()
    return roles

def get_user():
    query = 'SELECT * FROM users'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    user = cursor.fetchall()
    cursor.close()
    return user

def get_roles():
    query = 'SELECT * FROM roles'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    roles = cursor.fetchall()
    cursor.close()
    return roles

@app.route('/')
def index():
    books=[]
    querry = 'SELECT * FROM books ORDER BY year DESC'
    page = int(request.args.get('page', 1))
    count = 0
    try:
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(querry)
        books = cursor.fetchall()
        cursor.close()
        count = math.ceil(len(books) / PER_PAGE)
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash('Произошла ошибка при загрузке страницы.', 'danger')
    return render_template('index.html', books=books[PER_PAGE * (page - 1) : PER_PAGE * page], count=count, page=page)


#@app.route('/users/')
#@login_required
#def show_users():
    query = '''
        SELECT users.*, roles.name as role_name
        FROM users
        LEFT JOIN roles
        on roles.id = users.role_id
        '''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    users = cursor.fetchall()
    cursor.close()
    return render_template('users/index.html',users=users)


@app.route('/books/create', methods = ['POST', 'GET'])
@login_required
@check_rights('create')
def create():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        year = request.form['year']
        publishing = request.form['publishing']
        author = request.form['author']
        pages = request.form['pages']
        try:
            querry = '''
                insert into books (name, description, year, publishing, author, pages)
                VALUES (%s, %s, %s, %s, %s, %s)
                '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(querry, (name, description, year, publishing, author, pages))
            db.connection().commit()
            flash(f'Книга {name} успешно добавлена.', 'success')
            cursor.close()
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При добавлении книги произошла ошибка.', 'danger')
            return render_template('books/create.html')

    return render_template('books/create.html')


@app.route('/books/show/<int:book_id>')
@login_required
@check_rights('show')
def show(book_id):
    querry = 'SELECT * FROM books WHERE books.id=%s'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(querry, (book_id,))
    book = cursor.fetchone()
    cursor.close()
    return render_template('books/show.html', book = book)


@app.route('/books/edit/<int:book_id>', methods=["POST", "GET"])
@login_required
@check_rights('edit')
def edit(book_id):
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        year = request.form['year']
        publishing = request.form['publishing']
        author = request.form['author']
        pages = request.form['pages']
        try:
            if current_user.is_admin() and current_user.is_moderator():
                role_id = request.form['role_id']
                query = '''
                    UPDATE users set first_name = %s, last_name = %s, middle_name = %s, role_id = %s where id = %s
                    '''
                cursor = db.connection().cursor(named_tuple=True)
                cursor.execute(query, (first_name, last_name, middle_name, role_id, user_id))
                db.connection().commit()
            else:
                query = '''
                    UPDATE users set first_name = %s, last_name = %s, middle_name = %s where id = %s
                    '''
                cursor = db.connection().cursor(named_tuple=True)
                cursor.execute(query, (first_name, last_name, middle_name, user_id))
                db.connection().commit()
            flash(f'Данные пользователя {first_name} успешно обновлены.', 'success')
            cursor.close()
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При обновлении пользователя произошла ошибка.', 'danger')
            return render_template('users/edit.html')

    query = '''
        SELECT users.*, roles.name as role_name
        FROM users
        LEFT JOIN roles
        on roles.id = users.role_id
        where users.id=%s
        '''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('users/edit.html', user=user, roles=roles)

@app.route('/books/delete/')
@login_required
@check_rights('delete')
def delete():
    try:
        book_id = request.args.get('book_id')
        querry = '''
            DELETE from books where id = %s
            '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(querry, (book_id,))
        db.connection().commit()
        flash(f'Книга успешно удалена.', 'success')
        cursor.close()
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При удалении книги произошла ошибка.', 'danger')
        return render_template('index.html', book_id=book_id)

    return redirect(url_for('index'))
