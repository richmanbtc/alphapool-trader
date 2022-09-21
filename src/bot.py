import time
import traceback
import numpy as np
import pandas as pd
from .utils import (
    fetch_positions,
    fetch_tickers,
    fetch_collateral,
    symbol_to_ccxt_symbol,
    normalize_amount,
)


class Bot:
    def __init__(self, client=None, logger=None, leverage=None,
                 alphapool_client=None):
        self._client = client
        self._logger = logger
        self._order_interval = 5
        self._loop_interval = 60
        self._leverage = leverage
        self._alphapool_client = alphapool_client

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

        markets = {market['symbol']: market for market in self._client.fetch_markets()}
        collateral = fetch_collateral(self._client)
        self._logger.info('collateral {}'.format(collateral))

        df_ticker = fetch_tickers(self._client)

        df_current = fetch_positions(self._client)

        df_target = fetch_target_positions(timestamp=now, agent_base_url=self._agent_base_url)
        df_target.index = df_target.index.map(lambda x: symbol_to_ccxt_symbol(x, exchange=self._client.id))

        df_target = df_target.join(df_ticker[['close']], on='symbol', how='left')
        df_target['position'] = self._leverage * df_target['position'] * collateral / df_target['close']

        df = pd.merge(
            df_target,
            df_current,
            how='outer', suffixes=['', '_current'],
            left_index=True, right_index=True
        )
        df = df.fillna(0)
        df['signed_amount'] = df['position'] - df['position_current']

        self._logger.debug('df {}'.format(df))

        for symbol in df.index:
            if symbol not in df_ticker.index:
                self._logger.debug('order loop skipped. df_ticker not found. symbol {}'.format(symbol))
                continue

            self._logger.debug('order loop symbol {}'.format(symbol))
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

