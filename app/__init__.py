from flask import Flask
from flask_pymongo import PyMongo

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')

mongo = PyMongo(app)