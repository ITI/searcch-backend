from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from instance.config import Config


# setup flask app
app = Flask(__name__, instance_relative_config=True)

# set up configurations
app.config.from_object(Config)
app.config.from_object('config')
app.config.from_pyfile('config.py')

# initialize all extensions
db = SQLAlchemy(app)
ma = Marshmallow(app)
migrate = Migrate(app, db)

from app.routes.artifacts import artifacts_bp

# register blueprints for different API endpoints
app.register_blueprint(artifacts_bp, url_prefix='/artifacts')
# app.register_blueprint(favourites, url_prefix='favourites')
# app.register_blueprint(importer, url_prefix='importer')
# app.register_blueprint(ratings, url_prefix='ratings')
# app.register_blueprint(reviews, url_prefix='reviews')
# app.register_blueprint(users, url_prefix='users')
