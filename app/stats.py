import csv
from io import StringIO
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from models import db, Visit, Book, User
from sqlalchemy import func

stats_bp = Blueprint('stats', __name__, template_folder='templates', url_prefix='/stats')

def admin_only(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*a, **kw):
        if not current_user.is_authenticated or current_user.role.name!='admin':
            flash('Недостаточно прав', 'warning')
            return redirect(url_for('main.index'))
        return f(*a, **kw)
    return wrapper

@stats_bp.route('/', methods=['GET'])
@stats_bp.route('/log', methods=['GET'])
@admin_only
def stats_log():
    page = request.args.get('page', 1, type=int)
    pagination = Visit.query.order_by(Visit.timestamp.desc()) \
                      .paginate(page=page, per_page=10, error_out=False)
    return render_template('stats_log.html', pagination=pagination)

@stats_bp.route('/log/export')
@admin_only
def export_log():
    q = Visit.query.order_by(Visit.timestamp.desc()).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['№','Пользователь','Книга','Дата'])
    for i,v in enumerate(q,1):
        user = f"{v.user.last_name} {v.user.first_name}" if v.user else "Гость"
        writer.writerow([i, user, v.book.title, v.timestamp])
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition":
            f"attachment;filename=log_{datetime.utcnow().date()}.csv"}
    )

@stats_bp.route('/summary', methods=['GET','POST'])
@admin_only
def stats_summary():
    page = request.args.get('page',1,type=int)
    df = request.values.get('date_from','')
    dt = request.values.get('date_to','')
    q = db.session.query(Book.title, func.count(Visit.id).label('cnt')) \
          .join(Visit).filter(Visit.user_id.isnot(None))
    if df:
        q = q.filter(Visit.timestamp>=df)
    if dt:
        q = q.filter(Visit.timestamp<=(dt+' 23:59:59'))
    q = q.group_by(Book.id).order_by(func.count(Visit.id).desc())
    pag = q.paginate(page=page, per_page=10, error_out=False)
    return render_template('stats_summary.html',
        pagination=pag, date_from=df, date_to=dt
    )

@stats_bp.route('/summary/export')
@admin_only
def export_summary():
    df = request.values.get('date_from','')
    dt = request.values.get('date_to','')
    q = db.session.query(Book.title, func.count(Visit.id).label('cnt')) \
          .join(Visit).filter(Visit.user_id.isnot(None))
    if df: q = q.filter(Visit.timestamp>=df)
    if dt: q = q.filter(Visit.timestamp<=(dt+' 23:59:59'))
    q = q.group_by(Book.id).order_by(func.count(Visit.id).desc()).all()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['№','Книга','Просмотров'])
    for i,(title,cnt) in enumerate(q,1):
        writer.writerow([i, title, cnt])
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition":
            f"attachment;filename=summary_{datetime.utcnow().date()}.csv"}
    )
