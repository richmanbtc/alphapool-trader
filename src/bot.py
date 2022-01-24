import time
import numpy as np
import pandas as pd
from .agent_api import fetch_target_positions
from .utils import (
    fetch_positions,
    fetch_tickers,
    fetch_collateral,
    symbol_to_ccxt_symbol,
    normalize_amount,
)


class Bot:
    def __init__(self, client=None, logger=None, leverage=None,
                 agent_base_url=None, exchange=None):
        self._client = client
        self._logger = logger
        self._order_interval = 5
        self._loop_interval = 60
        self._leverage = leverage
        self._agent_base_url = agent_base_url
        self._exchange = exchange

    def run(self):
        while True:
            try:
                self._step()
            except Exception as e:
                self._logger.error(e)
            time.sleep(self._loop_interval)

    def _step(self):
        now = time.time()

        markets = {market['symbol']: market for market in self._client.fetch_markets()}
        collateral = fetch_collateral(self._client)
        self._logger.info('collateral {}'.format(collateral))

        df_ticker = fetch_tickers(self._client)

        df_current = fetch_positions(self._client)
        df_target = fetch_target_positions(timestamp=now, agent_base_url=self._agent_base_url)
        df_target.index = df_target.index.map(lambda x: symbol_to_ccxt_symbol(x, exchange=self._exchange))

        df_target = df_target.join(df_ticker[['close']], on='symbol', how='left')
        df_target['position'] = self._leverage * df_target['position'] * collateral / df_target['close']

        df = df_target.join(df_current, how='outer', on='symbol', rsuffix='_current')
        df = df.fillna(0)
        df['signed_amount'] = df['position'] - df['position_current']

        for symbol in df.index:
            signed_amount = df.loc[symbol, 'signed_amount']

            signed_amount = normalize_amount(
                signed_amount,
                price=df_ticker.loc[symbol, 'close'],
                market=markets[symbol],
            )

            if signed_amount == 0:
                continue

            time.sleep(self._order_interval)
            self._logger.info('create_order symbol {} signed_amount {}'.format(
                symbol, signed_amount
            ))
            self._client.create_order(
                symbol,
                'market',
                'sell' if signed_amount < 0 else 'buy',
                np.abs(signed_amount),
            )

