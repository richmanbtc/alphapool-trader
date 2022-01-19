import ccxt
import pandas as pd
import numpy as np


def create_ccxt_client(exchange, api_key=None, api_secret=None, subaccount=None):
    headers = {}
    if exchange == 'ftx' and subaccount is not None and subaccount != '':
        headers['FTX-SUBACCOUNT'] = subaccount

    client = getattr(ccxt, exchange)({
        'apiKey': api_key,
        'secret': api_secret,
        'headers': headers
    })
    return client


def symbol_to_ccxt_symbol(symbol, exchange=None):
    if exchange == 'ftx':
        return symbol + '/USD:USD'
    elif exchange == 'binance':
        return symbol + 'USDT'
    else:
        raise Exception('not implemented')


def round_to_execution_start_at(x):
    day_seconds = 24 * 60 * 60
    execution_start_at_shift = 30 * 60
    return _round_int(int(x) - execution_start_at_shift, day_seconds) + execution_start_at_shift


def normalize_amount(x, price=None, market=None):
    if x < 0:
        return -normalize_amount(-x, price=price, market=market)

    limits = market['limits']['amount']
    cost_limits = market['limits']['cost']

    if 'min' in cost_limits and cost_limits['min'] is not None:
        if x * price < 2 * cost_limits['min']:  # 2: 安全率
            x = 0.0

    if 'min' in limits and limits['min'] is not None:
        if x < limits['min']:
            x = 0.0

    if 'max' in limits and limits['max'] is not None:
        x = min(limits['max'], x)

    return round_precision(x, market['precision']['amount'])


def round_precision(x, precision):
    if type(precision) is int:
        return round(x, precision)
    else:
        return round(x / precision) * precision


def fetch_positions(client):
    poss = client.fetch_positions()
    df = pd.DataFrame(poss)
    df['position'] = df['contracts'] * np.where(df['side'] == 'long', 1, -1)
    df = df[['symbol', 'position']]
    df = df.set_index('symbol')
    return df


def fetch_tickers(client):
    tickers = client.fetch_tickers()
    df = pd.DataFrame([tickers[key] for key in tickers])
    df = df[['symbol', 'close']]
    df = df.set_index('symbol')
    return df


def fetch_collateral(client):
    if client.id == 'ftx':
        res = client.privateGetAccount()
        return res['result']['collateral']
    else:
        raise Exception('not implemented')


def _round_int(a, b):
    return ((a + b // 2) // b) * b
