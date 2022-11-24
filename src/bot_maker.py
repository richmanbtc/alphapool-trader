import math
import time
import traceback
import numpy as np
import pandas as pd
from .processing import preprocess_df, calc_portfolio_positions
from .utils import (
    fetch_positions,
    fetch_collateral,
    symbol_to_ccxt_symbol,
    normalize_amount,
    cancel_all_orders,
    set_leverage
)


class BotMaker:
    def __init__(self, client=None, logger=None, leverage=None,
                 alphapool_client=None, model_id=None):
        self._client = client
        self._logger = logger
        self._order_interval = 5
        self._loop_interval = 60
        self._leverage = leverage
        self._alphapool_client = alphapool_client
        self._model_id = model_id
        self._leverage_set = {}

    def run(self):
        while True:
            try:
                self._step()
            except Exception as e:
                self._logger.error(e)
                self._logger.error(traceback.format_exc())

            time.sleep(self._loop_interval)

    def _step(self):
        now = time.time()
        interval = 300
        execution_time = math.floor(time.time() / interval) * interval
        execution_time = pd.to_datetime(execution_time, unit="s", utc=True)
        self._logger.info('now {} execution_time {}'.format(now, execution_time))

        df = self._alphapool_client.get_positions(
            tournament="crypto",
            min_timestamp=int(now - 24 * 60 * 60),
        )

        df = preprocess_df(df, execution_time)
        df = calc_portfolio_positions(df)
        df = df.loc[df.index.get_level_values('model_id') == self._model_id]
        row = df.iloc[-1]
        self._logger.info('row {}'.format(row))

        collateral = fetch_collateral(self._client)
        self._logger.info('collateral {}'.format(collateral))

        df_current_pos = fetch_positions(self._client)
        self._logger.info('df_current_pos {}'.format(df_current_pos))
        markets = {market['symbol']: market for market in self._client.fetch_markets()}

        for col in row.index:
            if not col.startswith("p."):
                continue
            symbol = col.replace("p.", "")
            ccxt_symbol = symbol_to_ccxt_symbol(symbol, exchange=self._client.id)

            if ccxt_symbol not in markets:
                self._logger.warn('symbol {} not exist. skip'.format(ccxt_symbol))
                continue

            target_pos = row[col]

            time.sleep(self._order_interval)

            ticker = self._client.fetch_ticker(ccxt_symbol)
            price = ticker['last']

            if ccxt_symbol in df_current_pos.index:
                cur_pos = df_current_pos.loc[ccxt_symbol, 'position'] * markets[ccxt_symbol]['contractSize']
            else:
                cur_pos = 0.0
            signed_amount = target_pos * collateral / price - cur_pos
            if signed_amount * cur_pos < 0:
                reduce_only = True
                signed_amount = np.sign(signed_amount) * min(np.abs(signed_amount), np.abs(cur_pos))
            else:
                reduce_only = False

            self._sync_order(
                markets[ccxt_symbol],
                signed_amount,
                price,
                reduce_only
            )

    def _sync_order(self, market, signed_amount, price, reduce_only):
        symbol = market['symbol']

        self._logger.info('_sync_order symbol {} signed_amount {} price {}'.format(
            symbol, signed_amount, price
        ))

        signed_amount /= market['contractSize']

        signed_amount = normalize_amount(
            signed_amount,
            price=price,
            market=market,
        )

        cancel_all_orders(self._client, symbol)

        if signed_amount == 0:
            self._logger.info('normalized amount zero. skip')
            return

        # fetch latest ticker
        ob = self._client.fetch_order_book(symbol=symbol)

        best_ask = ob['asks'][0][0]
        best_bid = ob['bids'][0][0]
        params = {}
        order_type = 'limit'
        if self._client.id == 'binance':
            params['timeInForce'] = 'GTX'
            params['reduceOnly'] = 'true' if reduce_only else 'false'
        elif self._client.id == 'okx':
            order_type = 'post_only'
            params['reduceOnly'] = 'true' if reduce_only else 'false'

        self.ensure_leverage(market, 10)

        self._logger.info('create_order symbol {} signed_amount {} best_ask {} best_bid {} params {}'.format(
            symbol, signed_amount, best_ask, best_bid, params
        ))
        self._client.create_order(
            symbol,
            order_type,
            'sell' if signed_amount < 0 else 'buy',
            np.abs(signed_amount),
            best_ask if signed_amount < 0 else best_bid,
            params
        )

    def ensure_leverage(self, market, leverage):
        symbol = market['symbol']
        if symbol in self._leverage_set:
            return
        self._logger.info('set_leverage symbol {} leverage {}'.format(
            symbol, leverage
        ))
        set_leverage(self._client, market, leverage)
        self._leverage_set[symbol] = True
