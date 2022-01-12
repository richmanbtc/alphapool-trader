FROM python:3.6.15

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir \
    ccxt==1.67.18 \
    coverage==6.2 \
    numpy==1.19.5 \
    pandas==1.1.5
