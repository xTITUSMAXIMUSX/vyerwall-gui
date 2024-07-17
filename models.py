from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_migrate import Migrate

# Initialize Flask-SQLAlchemy
db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)

class APISettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=False)
    apikey = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=443)
    protocol = db.Column(db.String(10), nullable=False, default='https')
    verify_ssl = db.Column(db.Boolean, nullable=False, default=False)
    connected = db.Column(db.Boolean, nullable=False, default=False)

