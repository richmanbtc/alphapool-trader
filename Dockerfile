FROM python:3.10.6

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir \
    ccxt==1.93.98 \
    coverage==6.2 \
    numpy==1.23.3 \
    pandas==1.5.2 \
    schedule==1.1.0 \
    "git+https://github.com/richmanbtc/alphapool.git@v0.1.5#egg=alphapool" \
    dataset==1.5.2 \
    psycopg2==2.9.3

ADD . /app
ENV ALPHAPOOL_LOG_LEVEL debug
WORKDIR /app
CMD python -m src.main
