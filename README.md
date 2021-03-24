# searcch-backend
SEARCCH Backend Subsystems

## Installation
1. Setup a virtual environment
```bash
virtualenv -p python3 venv
source venv/bin/activate
```
2. Install project dependencies
```bash
pip3 install -r requirements.txt
```
3. Run the app server
```bash
# Using flask run
export FLASK_APP=run:app
export FLASK_CONFIG=development
export FLASK_INSTANCE_CONFIG_FILE=config.py
flask run --host=0.0.0.0 --port=80

# Using gunicorn
sudo /home/hardik/.local/bin/gunicorn --config gunicorn_conf.py run:app
```

## Setup Database - MongoDB
1. Install MongoDB from this [link](https://hackernoon.com/how-to-install-and-secure-mongodb-in-amazon-ec2-in-minutes-90184283b0a1)
2. Setup admin and user for zenodo_artifacts collection
3. Restore the data for this collection

## Setup Database - PostgreSQL
1. To setup schema in empty database
```python3
from app import db
db.create_all()
```

```bash
flask db init
# reflects changes made in Flask in the database
flask db migrate
# executes migration and creates the tables
flask db upgrade
```
