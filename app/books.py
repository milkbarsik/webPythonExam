from datetime import date, datetime, timedelta
import os
import hashlib
import markdown
import bleach

from flask import (
    Blueprint, render_template, request, redirect, session,
    url_for, flash, current_app, send_from_directory
)
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename
from models import Visit, db, Book, Genre, Cover, Review, login_manager
from werkzeug.datastructures import MultiDict

main = Blueprint('main', __name__, template_folder='templates')

ALLOWED_EXT = {'png','jpg','jpeg','gif'}
BLEACH_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({
    'p','pre','code','h1','h2','h3','ul','ol','li','blockquote','img'
})
BLEACH_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    'img': ['src','alt','title']
}

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXT

def render_md(md_text):
    html = markdown.markdown(md_text)
    return bleach.clean(html, tags=BLEACH_TAGS, attributes=BLEACH_ATTRS)

def role_required(*roles):
    from functools import wraps
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kw):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role.name not in roles:
                flash('У вас недостаточно прав для выполнения данного действия.', 'warning')
                return redirect(url_for('main.index'))
            return f(*args, **kw)
        return wrapper
    return deco

@main.route('/')
@main.route('/page/<int:page>')
def index(page=1):
    q = request.args.get('q','').strip()
    query = Book.query
    if q:
        query = query.filter(Book.title.ilike(f'%{q}%'))

    pagination = query.order_by(Book.year.desc()) \
                  .paginate(page=page, per_page=10, error_out=False)

    three_months_ago = datetime.now() - timedelta(days=90)
    popular = (
        db.session.query(Book, func.count(Visit.id).label('cnt'))
        .join(Visit)
        .filter(Visit.timestamp >= three_months_ago)
        .group_by(Book.id)
        .order_by(func.count(Visit.id).desc())
        .limit(5)
        .all()
    )

    sid = session['visitor_id']
    uid = current_user.get_id()
    recent_q = Visit.query.filter_by(session_id=sid)
    if uid:
        recent_q = recent_q.filter(Visit.user_id==uid)
    records = recent_q.order_by(Visit.timestamp.desc()).limit(20).all()
    seen = set()
    recent = []
    for v in records:
        if v.book_id not in seen:
            recent.append(v.book)
            seen.add(v.book_id)
        if len(recent)>=5:
            break

    return render_template('index.html',
        pagination=pagination, q=q,
        popular=popular, recent=recent
    )

@main.route('/books/<int:book_id>')
def book_view(book_id):
    book = Book.query.get_or_404(book_id)
    sid = session['visitor_id']
    uid = current_user.get_id()

    today = date.today()
    cnt = Visit.query.filter(
        Visit.book_id==book_id,
        Visit.session_id==sid,
        func.date(Visit.timestamp)==today
    )
    if uid:
        cnt = cnt.filter(Visit.user_id==uid)
    cnt = cnt.count()

    if cnt < 10:
        v = Visit(book_id=book_id, session_id=sid, user_id=uid)
        db.session.add(v)
        db.session.commit()

    book_html = render_md(book.description)
    existing = None
    if current_user.is_authenticated:
        existing = Review.query.filter_by(book_id=book_id, user_id=uid).first()

    return render_template('book_view.html',
        book=book, book_html=book_html, existing_review=existing
    )

@main.route('/books/<int:book_id>/review', methods=['GET','POST'])
@login_required
def book_review(book_id):
    book = Book.query.get_or_404(book_id)
    if Review.query.filter_by(book_id=book.id, user_id=current_user.id).first():
        return redirect(url_for('main.book_view', book_id=book.id))
    if request.method == 'POST':
        try:
            rating = int(request.form['rating'])
            text   = request.form['text']
            review = Review(
                book_id=book.id,
                user_id=current_user.id,
                rating=rating,
                text=text
            )
            db.session.add(review)
            db.session.commit()
            flash('Рецензия успешно сохранена.', 'success')
            return redirect(url_for('main.book_view', book_id=book.id))
        except Exception:
            db.session.rollback()
            flash('При сохранении рецензии возникла ошибка.', 'danger')
    return render_template('review_form.html', book=book)

@main.route('/reviews/<int:review_id>/delete', methods=['POST'])
@role_required('admin','moderator')
def review_delete(review_id):
    review = Review.query.get_or_404(review_id)
    book_id = review.book_id
    try:
        db.session.delete(review)
        db.session.commit()
        flash('Рецензия удалена.', 'success')
    except Exception:
        db.session.rollback()
        flash('При удалении рецензии возникла ошибка.', 'danger')
    return redirect(url_for('main.book_view', book_id=book_id))


@main.route('/books/create', methods=['GET','POST'])
@role_required('admin')
def book_create():
    genres = Genre.query.all()
    errors = {}
    form = request.form if request.method == 'POST' else MultiDict()

    if request.method == 'POST':
        file = request.files.get('cover')

        required = ['title','description','year','publisher','author','pages']
        if not all(form.get(f) for f in required):
            errors['general'] = 'Заполните все обязательные поля.'
            flash(errors['general'], 'danger')
            return render_template(
                'book_form.html',
                action='create',
                genres=genres,
                form=form,
                errors=errors,
                book=None
            )

        try:
            book = Book(
                title=form['title'],
                description=form['description'],
                year=int(form['year']),
                publisher=form['publisher'],
                author=form['author'],
                pages=int(form['pages'])
            )
            for gid in form.getlist('genres'):
                genre = Genre.query.get(int(gid))
                if genre:
                    book.genres.append(genre)

            db.session.add(book)
            db.session.flush()

            if file and allowed_file(file.filename):
                data = file.read()
                md5 = hashlib.md5(data).hexdigest()
                existing = Cover.query.filter_by(md5_hash=md5).first()
                if existing:
                    existing.book_id = book.id
                else:
                    ext = secure_filename(file.filename).rsplit('.',1)[1]
                    cover = Cover(
                        filename='',
                        mime_type=file.mimetype,
                        md5_hash=md5,
                        book_id=book.id
                    )
                    db.session.add(cover)
                    db.session.flush()
                    filename = f"{cover.id}.{ext}"
                    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    with open(path, 'wb') as f:
                        f.write(data)
                    cover.filename = filename

            db.session.commit()
            flash('Книга успешно добавлена.', 'success')
            return redirect(url_for('main.book_view', book_id=book.id))
        except Exception:
            db.session.rollback()
            errors['general'] = 'При сохранении книги возникла ошибка.'
            flash(errors['general'], 'danger')
            return render_template(
                'book_form.html',
                action='create',
                genres=genres,
                form=form,
                errors=errors,
                book=None
            )

    return render_template(
        'book_form.html',
        action='create',
        genres=genres,
        form=form,
        errors=errors,
        book=None
    )


@main.route('/books/<int:book_id>/edit', methods=['GET','POST'])
@role_required('admin','moderator')
def book_edit(book_id):
    book = Book.query.get_or_404(book_id)
    genres = Genre.query.all()
    errors = {}
    form = request.form if request.method == 'POST' else MultiDict()

    if request.method == 'POST':
        form = request.form
        try:
            book.title       = form['title']
            book.description = form['description']
            book.year        = int(form['year'])
            book.publisher   = form['publisher']
            book.author      = form['author']
            book.pages       = int(form['pages'])

            book.genres.clear()
            for gid in form.getlist('genres'):
                genre = Genre.query.get(int(gid))
                if genre:
                    book.genres.append(genre)

            db.session.commit()
            flash('Книга успешно обновлена.', 'success')
            return redirect(url_for('main.book_view', book_id=book.id))
        except Exception:
            db.session.rollback()
            errors['general'] = 'При обновлении книги возникла ошибка.'
            flash(errors['general'], 'danger')
            return render_template(
                'book_form.html',
                action='edit',
                genres=genres,
                form=form,
                errors=errors,
                book=book
            )

    return render_template(
        'book_form.html',
        action='edit',
        genres=genres,
        form=form,
        errors=errors,
        book=book
    )


@main.route('/books/<int:book_id>/delete', methods=['POST'])
@role_required('admin')
def book_delete(book_id):
    book = Book.query.get_or_404(book_id)
    try:
        if book.cover:
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover.filename)
            if os.path.exists(path):
                os.remove(path)
        db.session.delete(book)
        db.session.commit()
        flash('Книга успешно удалена.', 'success')
    except Exception:
        db.session.rollback()
        flash('При удалении книги возникла ошибка.', 'danger')
    return redirect(url_for('main.index'))

@main.route('/covers/<filename>')
def covers(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
