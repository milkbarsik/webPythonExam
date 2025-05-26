from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User

auth_bp = Blueprint('auth', __name__, template_folder='templates', url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        login_val = request.form['login'].strip()
        pwd       = request.form['password']
        remember  = 'remember' in request.form
        user = User.query.filter_by(login=login_val).first()
        if user and user.check_password(pwd):
            login_user(user, remember=remember)
            flash('Вы успешно вошли в систему.', 'success')
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('Невозможно аутентифицироваться с указанными логином и паролем.', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('main.index'))
