from app import app
from models import db, Role, User, Genre, Visit


def seed():
    roles = [
        ('admin',     'Суперпользователь, полный доступ'),
        ('moderator', 'Модератор, может редактировать книги и модерацию рецензий'),
        ('user',      'Обычный пользователь, может оставлять рецензии')
    ]
    for name, desc in roles:
        if not Role.query.filter_by(name=name).first():
            db.session.add(Role(name=name, description=desc))
    db.session.commit()
    print("Роли созданы или подтверждены.")
    
    genre_names = [
        'Fantasy',
        'Science Fiction',
        'Mystery',
        'Romance',
        'Historical',
        'Thriller'
    ]
    for name in genre_names:
        if not Genre.query.filter_by(name=name).first():
            db.session.add(Genre(name=name))
    print("Жанры созданы или подтверждены.")

    db.session.commit()

    users_to_create = [
        ('admin', 'qwe', 'Романихин', 'Михаил', 'Романович', 'admin'),
        ('moder', 'qwe', 'Иванов', 'Иван', 'Иванович', 'moderator'),
        ('user', 'qwe', 'Петров', 'Пётр', 'Петрович', 'user'),
    ]
    

    for login_val, pwd, last, first, patron, role_name in users_to_create:
        if not User.query.filter_by(login=login_val).first():
            role = Role.query.filter_by(name=role_name).first()
            u = User(
                login=login_val,
                last_name=last,
                first_name=first,
                patronymic=patron,
                role_id=role.id
            )
            u.set_password(pwd)
            db.session.add(u)
            print(f"Создан пользователь '{login_val}' с ролью '{role_name}'.")
        else:
            print(f"Пользователь '{login_val}' уже существует.")
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Таблицы созданы.")
        seed()
