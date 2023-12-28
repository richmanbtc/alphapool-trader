FROM python:3.10.6

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir \
    ccxt==4.2.1 \
    coverage==6.2 \
    numpy==1.23.3 \
    pandas==1.5.2 \
    parameterized==0.8.1 \
    "git+https://github.com/richmanbtc/alphapool.git@v0.1.5#egg=alphapool" \
    "git+https://github.com/richmanbtc/ccxt_rate_limiter.git@v0.0.6#egg=ccxt_rate_limiter" \
    dataset==1.5.2 \
    psycopg2==2.9.3 \
    SQLAlchemy==1.4.45 \
    retry==0.9.2 \
    requests==2.28.2 \
    numpyencoder==0.3.0

ADD . /app
ENV ALPHAPOOL_LOG_LEVEL debug
WORKDIR /app
CMD python -m src.main
