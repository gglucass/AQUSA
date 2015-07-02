#!/usr/bin/env python

from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand
import os
import subprocess

from app import app, models, analyzers, db

app.config.from_pyfile('../config.py')

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

def translate():
  subprocess.call('pybabel init -i messages.pot -d app/translations -l en && pybabel compile -d app/translations', shell=True)

manager.add_command('translate', translate())

if __name__ == '__main__':
  manager.run()