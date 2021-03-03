FROM pypy:3.7-slim-buster

WORKDIR /app

COPY . .

RUN apt update && apt install -y build-essential libpq-dev && pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gevent && mkdir logs

#ENV FLASK_INSTANCE_CONFIG_FILE=/app/config-development.py

Expose 80

CMD ["gunicorn","--config","gunicorn_conf.py","run:app"]
