from operator import itemgetter
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

    if exchange == 'binance':
        _override_binance_create_order_request(client)

    return client

def symbol_to_ccxt_symbol(symbol, exchange):
    if exchange == 'ftx':
        return symbol + '/USD:USD'
    elif exchange == 'binance':
        return symbol + '/USDT:USDT'
    elif exchange == 'bybit':
        return symbol + '/USDT:USDT'
    elif exchange == 'okx':
        return symbol + '/USDT:USDT'
    elif exchange == 'kucoinfutures':
        return symbol + '/USDT:USDT'
    elif exchange == 'bitflyer':
        return symbol + '/JPY:JPY'
    else:
        raise Exception('not implemented')


def ccxt_symbol_to_symbol(symbol):
    return symbol.replace('/USD:USD', '').replace('/USDT', '').replace(':USDT', '').replace('/JPY:JPY', '')


def normalize_amount(x, price=None, market=None, reduce_only=False):
    if x < 0:
        return -normalize_amount(-x, price=price, market=market, reduce_only=reduce_only)

    limits = market['limits']['amount']
    cost_limits = market['limits']['cost']

    if not reduce_only:
        if 'min' in cost_limits and cost_limits['min'] is not None:
            if x * price < 2 * cost_limits['min']:  # 2: safety factor
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
    if client.id == 'bitflyer':
        res = client.privateGetGetpositions({'product_code': 'FX_BTC_JPY'})
        pos = 0.0
        for item in res:
            pos += float(item['size']) * (1 if item['side'] == 'BUY' else -1)
        df = pd.DataFrame([
            {
                'symbol': 'BTC/JPY:JPY',
                'position': pos,
            }
        ])
        df = df.set_index('symbol')
        return df

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


def fetch_collateral(client, account_type=None):
    if client.id == 'ftx':
        res = client.privateGetAccount()
        return float(res['result']['collateral'])
    elif client.id == 'binance':
        res = client.fapiPrivateV2GetAccount()
        return float(res['totalMarginBalance'])
    elif client.id == 'bybit':
        res = client.privateGetV5AccountWalletBalance({
            'accountType': 'UNIFIED' if account_type == 'unified' else 'CONTRACT',
            'coin': 'USDT',
        })
        return float(res['result']['list'][0]['coin'][0]['equity'])
    elif client.id == 'okx':
        res = client.privateGetAccountBalance()
        return float(res['data'][0]['totalEq'])
    elif client.id == 'kucoinfutures':
        res = client.futuresPrivateGetAccountOverview({
            'currency': 'USDT'
        })
        return float(res['data']['accountEquity'])
    elif client.id == 'bitflyer':
        res = client.privateGetGetcollateral()
        return float(res['collateral']) + float(res['open_position_pnl'])
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


def set_leverage(client, market, leverage, logger=None):
    symbol = market['symbol']
    max_leverage = market['limits']['leverage']['max']
    if max_leverage is not None:
        leverage = min(leverage, max_leverage)

    if client.id == 'kucoinfutures':
        tiers = client.fetch_market_leverage_tiers(symbol)
        tiers = [x for x in tiers if x['maxLeverage'] >= leverage]
        tier = min(tiers, key=itemgetter('maxLeverage'))
        if logger is not None:
            logger.debug(f'futuresPrivatePostPositionRiskLimitLevelChange symbol {symbol} tier {tier}')
        client.futuresPrivatePostPositionRiskLimitLevelChange({
            'symbol': market['id'],
            'level': tier['tier'],
        })
        return

    try:
        client.set_leverage(leverage, symbol)
    except BadRequest as e:
        if 'leverage not modified' in e.args[0]:
            return
        raise


def _override_binance_create_order_request(client):
    old_method = client.create_order_request

    def new_method(symbol, type, side, amount, price=None, params={}):
        use_bbo = 'priceMatch' in params and params['priceMatch'] is not None
        if not use_bbo:
            return old_method(symbol, type, side, amount, price=price, params=params)

        assert price is None
        res = old_method(symbol, type, side, amount, price=1, params=params)
        del res['price']
        return res

    client.create_order_request = new_method
