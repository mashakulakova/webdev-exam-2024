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

PER_PAGE = 3

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

def get_book(book_id):
    query = 'SELECT * FROM books WHERE id=%s'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (book_id,))
    book = cursor.fetchone()
    cursor.close()
    return book

def get_genres_book(book_id):
    
    query = """
    SELECT g.name 
    FROM genres g 
    JOIN book_genres gb ON g.id = gb.genre_id 
    WHERE gb.book_id = %s
    """
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (book_id,))
    genres = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    
    return genres


@app.route('/')
def index():
    books=[]
    query = '''
        SELECT b.*, GROUP_CONCAT(g.name SEPARATOR ', ') AS genres
        FROM books b
        LEFT JOIN book_genres bg ON b.id = bg.book_id
        LEFT JOIN genres g ON bg.genre_id = g.id
        GROUP BY b.id
        ORDER BY b.year DESC;
    '''
    page = int(request.args.get('page', 1))
    count = 0
    try:
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query)
        books = cursor.fetchall()
        cursor.close()
        count = math.ceil(len(books) / PER_PAGE)
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash('Произошла ошибка при загрузке страницы!', 'danger')
    return render_template('index.html', books=books[PER_PAGE * (page - 1) : PER_PAGE * page], count=count, page=page)

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
        genres = request.form.getlist('genres')
        try:
            querry = '''
                insert into books (name, description, year, publishing, author, pages)
                VALUES (%s, %s, %s, %s, %s, %s)
                '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(querry, (name, description, year, publishing, author, pages))
            db.connection().commit()
            if not genres:
                flash('Выберите жанр', 'warning')
                return render_template('books/edit.html', genres = get_genres())
            cursor.close()
            cursor = db.connection().cursor(named_tuple=True)

            querry = '''
                SELECT id FROM books where name=%s and description=%s
                '''
            cursor.execute(querry, (name, description, ))
            book_id = cursor.fetchone()
            for genre_id in genres:
                query = "INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)"
                cursor.execute(query, (book_id[0], genre_id,))
                db.connection().commit()
            
            flash(f'Книга {name} успешно добавлена.', 'success')
            cursor.close()
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При добавлении книги произошла ошибка.', 'danger')
            return render_template('books/create.html')

    return render_template('books/create.html', genres = get_genres())


@app.route('/books/show/<int:book_id>')
@login_required
@check_rights('show')
def show(book_id):
    querry = 'SELECT * FROM books WHERE books.id=%s'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(querry, (book_id,))
    book = cursor.fetchone()
    cursor.close()
    return render_template('books/show.html', book = book, genres = get_genres_book(book_id))

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
        genres = request.form.getlist('genres')
        
        try:
            query = '''
            UPDATE books set name = %s, description = %s, year = %s, publishing = %s, author = %s, pages = %s where id = %s
            '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query, (name, description, year, publishing, author, pages, book_id,))
            db.connection().commit()
            if not genres:
                flash('Выберите жанр', 'warning')
                return render_template('books/edit.html', book = get_book(book_id), genres = get_genres())
            
            query = "DELETE FROM book_genres WHERE book_id = %s"
            cursor.execute(query, (book_id,))
            db.connection().commit()

            for genre_id in genres:
                query = "INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)"
                cursor.execute(query, (book_id, genre_id,))
                db.connection().commit()

            flash(f'Книга {name} успешно отредактирована.', 'success')
            cursor.close()
            return render_template('books/edit.html', book=get_book(book_id), genres=get_genres())

        except mysql.connector.errors.DatabaseError as err:
            db.connection().rollback()
            flash(f'При редактировании книги произошла ошибка.{err}', 'danger')
            
            return render_template('books/edit.html', book = get_book(book_id), genres = get_genres())
        
    return render_template('books/edit.html', book = get_book(book_id), genres = get_genres())


@app.route('/books/delete/')  
@login_required  
@check_rights('delete')  
def delete():
    genres = request.form.getlist('genres')
    page = int(request.args.get('page', 1))
    count = 0
    try:  
        book_id = request.args.get('book_id')
        querry = "DELETE FROM books WHERE id = %s"
        cursor = db.connection().cursor(named_tuple=True)  
        cursor.execute(querry, (book_id,))  
        db.connection().commit()

        for genre_id in genres:
            query = "DELETE FROM book_genres WHERE book_id = %s AND genre_id = %s"
            cursor.execute(query, (book_id, genre_id,))
            db.connection().commit()

        db.connection().commit()  
        flash(f'Книга успешно удалена.', 'success')  
        cursor.close()

    except mysql.connector.errors.DatabaseError:  
        db.connection().rollback()  
        flash(f'При удалении книги произошла ошибка.', 'danger')  
        return render_template('index.html', book=get_book(book_id), genres=get_genres(), page=page, count=count)
  
    return redirect(url_for('index'))
