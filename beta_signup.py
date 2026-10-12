"""Beta registrations stored using the website's existing SQLAlchemy connection."""
import hmac
import os
import re
import secrets
from pathlib import Path

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


def init_beta_signup(app, db):
    signups = db.Table(
        'beta_signups',
        db.Column('id', db.Integer, primary_key=True),
        db.Column('name', db.String(120), nullable=False),
        db.Column('email', db.String(254), nullable=False, unique=True),
        db.Column('company', db.String(160), nullable=False),
        db.Column('current_security', db.Text, nullable=False),
        db.Column('created_at', db.DateTime, nullable=False, server_default=db.func.now()),
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[signups])

    beta = Blueprint('beta', __name__)
    app.config.setdefault('BETA_ADMIN_USERNAME', os.environ.get('BETA_ADMIN_USERNAME', 'admin'))
    app.config.setdefault('BETA_ADMIN_PASSWORD', os.environ.get('BETA_ADMIN_PASSWORD', ''))

    @beta.after_request
    def private_admin_response(response):
        if request.endpoint == 'beta.admin':
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
            response.vary.add('Authorization')
        return response

    @beta.get('/aiwaf/beta-signups')
    def admin():
        password = app.config.get('BETA_ADMIN_PASSWORD')
        if not password:
            abort(404)
        auth = request.authorization
        username = str(app.config.get('BETA_ADMIN_USERNAME', 'admin'))
        user_ok = hmac.compare_digest((auth.username or '').encode(), username.encode()) if auth and auth.type == 'basic' else False
        password_ok = hmac.compare_digest((auth.password or '').encode(), str(password).encode()) if auth and auth.type == 'basic' else False
        if not (user_ok and password_ok):
            return Response('Admin authentication required.', status=401,
                headers={'WWW-Authenticate': 'Basic realm="AIWAF Cloud submissions", charset="UTF-8"'})
        try:
            page = int(request.args.get('page', '1'))
            if page < 1 or page > 1000000:
                raise ValueError
        except ValueError:
            abort(400)
        page_size = 50
        total = db.session.execute(db.select(db.func.count()).select_from(signups)).scalar_one()
        rows = db.session.execute(db.select(signups).order_by(signups.c.created_at.desc(), signups.c.id.desc())
            .limit(page_size).offset((page - 1) * page_size)).mappings().all()
        return render_template('beta_admin.html', submissions=rows, total=total, page=page,
                               has_next=page * page_size < total)

    @app.context_processor
    def beta_form_defaults():
        if request.path != '/' and request.endpoint != 'beta.signup':
            return {}
        if 'beta_csrf' not in session:
            session['beta_csrf'] = secrets.token_urlsafe(32)
        return {'beta_csrf': session['beta_csrf']}

    @beta.post('/beta-signup')
    def signup():
        if request.content_length is not None and request.content_length > 8192:
            return 'Submission too large.', 413
        token = request.form.get('csrf_token', '')
        expected = session.get('beta_csrf', '')
        if not expected or not hmac.compare_digest(token.encode(), expected.encode()):
            return render_template('home.html', beta_error='Please reload the page and try again.'), 403
        # A filled trap receives the same confirmation without creating a record.
        if any(value.strip() for value in request.form.getlist('website')):
            return confirmation()
        fields = {key: request.form.get(key, '').strip() for key in
                  ('name', 'email', 'company', 'current_security')}
        limits = {'name': 120, 'email': 254, 'company': 160, 'current_security': 2000}
        error = None
        if any(not value or len(value) > limits[key] for key, value in fields.items()):
            error = 'Please complete all four fields within the displayed limits.'
        elif not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", fields['email']) or '..' in fields['email'] or len(fields['email'].split('@')[0]) > 64:
            error = 'Please enter a valid email address.'
        elif request.form.get('consent') != 'yes':
            error = 'Please agree to be contacted about the AIWAF Cloud beta.'
        if error:
            return render_template('home.html', beta_error=error, beta_values=fields), 422
        fields['email'] = fields['email'].lower()
        try:
            # Duplicate addresses preserve the original registration details.
            if db.session.execute(db.select(signups.c.id).where(signups.c.email == fields['email'])).first() is None:
                db.session.execute(signups.insert().values(**fields))
                db.session.commit()
        except IntegrityError:
            db.session.rollback()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception('Unable to save beta signup')
            return render_template('home.html', beta_error='We could not save your signup. Please try again shortly.', beta_values=fields), 503
        return confirmation()

    def confirmation():
        flash('Thanks! Your AIWAF Cloud beta signup has been received.', 'beta_success')
        return redirect(url_for('home', _anchor='beta-signup'), code=303)

    app.register_blueprint(beta)
    return signups
