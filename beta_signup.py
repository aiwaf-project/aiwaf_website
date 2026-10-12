"""Beta registrations stored using the website's existing SQLAlchemy connection."""
import hmac
import re
import secrets
from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
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
        if request.form.get('website'):
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
