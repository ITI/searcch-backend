from app.models import model
from app import routes
from flask import Flask
from instance.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# setup flask app
app = Flask(__name__, instance_relative_config=True)

# set up configurations
app.config.from_object(Config)
app.config.from_object('config')
app.config.from_pyfile('config.py')

# initialize all extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
