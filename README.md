# searcch-backend
SEARCCH Backend Subsystems

## Installation
1. Setup a virtual environment
```bash
virtualenv -p python3 venv
```
2. Install project dependencies
```bash
pip3 install -r requirements.txt
```
3. Run the app server
- Using flask run:
```bash
export FLASK_APP=run:app
flask run --host=0.0.0.0 --port=80
```

- Using gunicorn:
```bash
gunicorn --config gunicorn_conf.py run:app
```