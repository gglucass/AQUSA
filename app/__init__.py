import os
from flask import Flask
from flask_bootstrap import Bootstrap
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.babel import Babel

app = Flask(__name__)
app.config.from_pyfile('../config.py')
Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)
babel = Babel(app)

from app import views, models