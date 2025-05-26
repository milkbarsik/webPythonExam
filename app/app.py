from uuid import uuid4
from flask import Flask, session
from markupsafe import Markup
from models import db, login_manager
from auth import auth_bp
from stats import stats_bp
from books import main as books_bp, render_md
import os

def create_app():
    app = Flask(__name__, static_folder='static')
    app.config.update(
        SECRET_KEY='your-secret-key',
        SQLALCHEMY_DATABASE_URI='postgresql://postgres:barsik@localhost:5432/exam',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'covers')
    )
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации.'

    @app.before_request
    def ensure_visitor_id():
        if 'visitor_id' not in session:
            session['visitor_id'] = uuid4().hex

    app.jinja_env.filters['markdown'] = lambda text: Markup(render_md(text))

    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(stats_bp)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
