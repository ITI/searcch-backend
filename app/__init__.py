from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
import os
from config import app_config

# setup flask app
app = Flask(__name__, instance_relative_config=True)

# set up configurations
config_name = os.getenv('FLASK_CONFIG')
app.config.from_object(app_config[config_name])
app.config.from_object('config')
app.config.from_pyfile('config.py')

# initialize all extensions
db = SQLAlchemy(app)
ma = Marshmallow(app)
migrate = Migrate(app, db)

# register blueprints for different API endpoints
from app.routes.artifacts import artifacts_bp
from app.routes.favorites import favorites_bp

app.register_blueprint(artifacts_bp, url_prefix=app.config.get('APPLICATION_ROOT') + '/artifacts')
app.register_blueprint(favorites_bp, url_prefix=app.config.get('APPLICATION_ROOT') + '/favorites')
# app.register_blueprint(importer, url_prefix='importer')
# app.register_blueprint(ratings, url_prefix='ratings')
# app.register_blueprint(reviews, url_prefix='reviews')
# app.register_blueprint(users, url_prefix='users')
