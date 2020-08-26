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
flask run --host=0.0.0.0 --port=80

# Using gunicorn
sudo /home/ubuntu/.local/bin/gunicorn --config gunicorn_conf.py run:app
```

## Setup Database - MongoDB
1. Install MongoDB from this [link](https://hackernoon.com/how-to-install-and-secure-mongodb-in-amazon-ec2-in-minutes-90184283b0a1)
2. Setup admin and user for zenodo_artifacts collection
3. Restore the data for this collection

## Setup Database - PostgreSQL
