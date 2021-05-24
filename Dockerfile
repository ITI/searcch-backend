#
# 7.3.4 has a nasty bug that broke requests.get for us; and other
# things for others: https://foss.heptapod.net/pypy/pypy/-/issues/3441
#
#FROM pypy:3.7-slim-buster
FROM pypy:3.7-7.3.3-slim-buster

RUN \
  apt update \
  && apt install -y build-essential libpq-dev \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --upgrade pip setuptools wheel

WORKDIR /app

COPY requirements.txt .

RUN \
  pip3 install --no-cache-dir -r requirements.txt \
  && mkdir -p logs

COPY instance/ ./instance
COPY searcch_backend ./searcch_backend
COPY setup.cfg setup.py run.py ./

#ENV FLASK_INSTANCE_CONFIG_FILE=/app/config-development.py
ENV FLASK_APP=run:app

Expose 80

CMD ["gunicorn","--config","gunicorn_conf.py","run:app"]
#CMD ["flask","run","--host=0.0.0.0","--port=80"]
