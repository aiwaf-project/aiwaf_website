"""Beta form validation and persistence using a real temporary SQLite database."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from beta_signup import init_beta_signup


class BetaSignupTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
        self.app.config.update(TESTING=True, SECRET_KEY='test-only-secret',
            SQLALCHEMY_DATABASE_URI='sqlite:///' + str(Path(self.directory.name) / 'signups.db'))
        self.db = SQLAlchemy(self.app)
        self.table = init_beta_signup(self.app, self.db)
        self.app.add_url_rule('/', 'home', lambda: render_template('home.html'))
        self.client = self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as session:
            self.token = session['beta_csrf']
        self.fields = dict(name='Jane Doe', email='Jane@example.com', company='Example Inc',
                           current_security='Cloud WAF and application rate limits',
                           consent='yes', csrf_token=self.token)

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.engine.dispose()

    def rows(self):
        with self.app.app_context():
            return list(self.db.session.execute(self.db.select(self.table)).mappings())

    def test_success_and_confirmation(self):
        response = self.client.post('/beta-signup', data=self.fields, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your AIWAF Cloud beta signup has been received', response.data)
        row, = self.rows()
        self.assertEqual(row['name'], 'Jane Doe')
        self.assertEqual(row['email'], 'jane@example.com')
        self.assertEqual(row['company'], 'Example Inc')
        self.assertEqual(row['current_security'], self.fields['current_security'])
        self.assertIsNotNone(row['created_at'])
        with self.app.app_context():
            self.db.engine.dispose()
        self.assertEqual(len(self.rows()), 1)

    def test_duplicate_preserves_original(self):
        self.client.post('/beta-signup', data=self.fields)
        self.client.post('/beta-signup', data={**self.fields, 'email': 'JANE@EXAMPLE.COM', 'company': 'Replacement'})
        row, = self.rows()
        self.assertEqual(row['company'], 'Example Inc')

    def test_validation_preserves_and_escapes_input(self):
        for changes in ({'email': 'invalid'}, {'name': ''}, {'company': ''},
                        {'current_security': ''}, {'current_security': 'x' * 2001}, {'consent': ''}):
            with self.subTest(changes=list(changes)):
                response = self.client.post('/beta-signup', data={**self.fields, **changes})
                self.assertEqual(response.status_code, 422)
        response = self.client.post('/beta-signup', data={**self.fields, 'name': '<script>alert(1)</script>', 'email': 'invalid'})
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>alert(1)</script>', response.data)
        self.assertEqual(self.rows(), [])

    def test_missing_csrf_or_other_session_rejected(self):
        self.assertEqual(self.client.post('/beta-signup', data={**self.fields, 'csrf_token': ''}).status_code, 403)
        self.assertEqual(self.app.test_client().post('/beta-signup', data=self.fields).status_code, 403)
        self.assertEqual(self.rows(), [])

    def test_honeypot_does_not_save(self):
        response = self.client.post('/beta-signup', data={**self.fields, 'website': 'bot.example'})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.rows(), [])

    def test_oversized_submission_rejected(self):
        self.assertEqual(self.client.post('/beta-signup', data={**self.fields, 'current_security': 'x' * 9000}).status_code, 413)
        self.assertEqual(self.rows(), [])
