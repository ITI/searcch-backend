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
3. Run the app server using gunicorn
```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0


gunicorn -w 4 myapp:app
gunicorn -b 0.0.0.0:8080 application:app --access-logfile '-' -w 4
gunicorn application:app -b 0:8000 --access-logfile '-' -w 2 --worker-class gevent --threads 4 --timeout 600
```