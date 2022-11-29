import ccxt
import pandas as pd
import numpy as np
from ccxt.base.errors import BadRequest

def create_ccxt_client(exchange, api_key=None, api_secret=None,
                       api_password=None, subaccount=None):
    headers = {}
    options = {}

    if exchange == 'ftx' and subaccount is not None and subaccount != '':
        headers['FTX-SUBACCOUNT'] = subaccount
    if exchange == 'binance':
        options['defaultType'] = 'future'

    client = getattr(ccxt, exchange)({
        'apiKey': api_key,
        'secret': api_secret,
        'password': api_password,
        'headers': headers,
        'options': options,
    })
    return client


def symbol_to_ccxt_symbol(symbol, exchange=None):
    if exchange == 'ftx':
        return symbol + '/USD:USD'
    elif exchange == 'binance':
        return symbol + '/USDT'
    elif exchange == 'bybit':
        return symbol + '/USDT:USDT'
    elif exchange == 'okx':
        return symbol + '/USDT:USDT'
    else:
        raise Exception('not implemented')


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
    if df.shape[0] == 0:
        return pd.DataFrame(columns=['symbol', 'position']).set_index('symbol')
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
        return float(res['result']['collateral'])
    elif client.id == 'binance':
        res = client.fapiPrivateGetAccount()
        return float(res['totalMarginBalance'])
    elif client.id == 'bybit':
        res = client.privateGetV2PrivateWalletBalance({ 'coin': 'USDT' })
        return float(res['result']['USDT']['equity'])
    elif client.id == 'okx':
        res = client.privateGetAccountBalance()
        return float(res['data'][0]['totalEq'])
    else:
        raise Exception('not implemented')


def cancel_all_orders(client, symbol):
    if hasattr(client, 'cancel_all_orders'):
        client.cancel_all_orders(symbol=symbol)
        return

    orders = client.fetch_open_orders(symbol=symbol)
    if len(orders) == 0:
        return
    order_ids = [x['id'] for x in orders]
    client.cancel_orders(order_ids, symbol=symbol)


def set_leverage(client, market, leverage):
    symbol = market['symbol']
    max_leverage = market['limits']['leverage']['max']
    if max_leverage is not None:
        leverage = min(leverage, max_leverage)
    try:
        client.set_leverage(leverage, symbol)
    except BadRequest as e:
        if 'leverage not modified' in e.args[0]:
            return
        raise
