from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from sqlalchemy.orm import backref

db = SQLAlchemy()
login_manager = LoginManager()

class Role(db.Model):
    __tablename__ = 'roles'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    login         = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    last_name     = db.Column(db.String(50), nullable=False)
    first_name    = db.Column(db.String(50), nullable=False)
    patronymic    = db.Column(db.String(50))
    role_id       = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False)

    role    = db.relationship('Role', backref='users')
    reviews = db.relationship('Review', backref='user', cascade='all, delete-orphan')

    def set_password(self, pwd):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, pwd)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

book_genre = db.Table(
    'book_genre',
    db.Column('book_id',  db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id', ondelete='CASCADE'), primary_key=True),
)

class Genre(db.Model):
    __tablename__ = 'genres'
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Book(db.Model):
    __tablename__ = 'books'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year        = db.Column(db.Integer, nullable=False)
    publisher   = db.Column(db.String(255), nullable=False)
    author      = db.Column(db.String(255), nullable=False)
    pages       = db.Column(db.Integer, nullable=False)

    genres  = db.relationship('Genre', secondary=book_genre, backref='books')
    cover   = db.relationship('Cover', uselist=False, backref='book', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='book', cascade='all, delete-orphan')
    visits  = db.relationship('Visit', backref=backref('book', passive_deletes=True), cascade='all, delete-orphan', passive_deletes=True)

class Cover(db.Model):
    __tablename__ = 'covers'
    id        = db.Column(db.Integer, primary_key=True)
    filename  = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    md5_hash  = db.Column(db.String(64), unique=True, nullable=False)
    book_id   = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)

class Review(db.Model):
    __tablename__ = 'reviews'
    id         = db.Column(db.Integer, primary_key=True)
    book_id    = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    rating     = db.Column(db.Integer, nullable=False)
    text       = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

class Visit(db.Model):
    __tablename__ = 'visits'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    session_id = db.Column(db.String(64), nullable=False, index=True)
    book_id    = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    timestamp  = db.Column(db.DateTime, default=datetime.now, nullable=False)

    user = db.relationship('User', backref='visits')