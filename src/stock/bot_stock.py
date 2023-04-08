from collections import defaultdict
import time
import traceback
import numpy as np
import pandas as pd
from retry import retry


class BotStock:
    def __init__(self, client=None, logger=None, leverage=None,
                 alphapool_client=None, model_id=None, health_check_ping=None):
        self._client = client
        self._logger = logger
        self._leverage = leverage
        self._alphapool_client = alphapool_client
        self._model_id = model_id
        self._health_check_ping = health_check_ping

    def run(self):
        while True:
            is_opening = self._sleep_until_next_loop()

            @retry(tries=3, delay=3, logger=self._logger)
            def retry_step():
                self._step(is_opening)

            try:
                retry_step()
                self._health_check_ping()
            except Exception as e:
                self._logger.error(e)
                self._logger.error(traceback.format_exc())

    def _sleep_until_next_loop(self):
        day = 24 * 60 * 60
        now = time.time()
        if now % day < (5 * 60 + 30) * 60:
            next_loop = (now // day) * day + (5 * 60 + 30) * 60
            is_opening = False
        elif now % day < (23 * 60 + 30) * 60:
            next_loop = (now // day) * day + (23 * 60 + 30) * 60
            is_opening = True
        else:
            next_loop = (now // day) * day + day + (5 * 60 + 30) * 60
            is_opening = False
        self._logger.info('sleep until {}'.format(pd.to_datetime(next_loop, unit='s', utc=True)))
        while time.time() < next_loop:
            self._health_check_ping()
            time.sleep(60)
        return is_opening

    def _step(self, is_opening):
        self._logger.info('step is_opening {}'.format(is_opening))

        target_pos = self._calc_target_positions(is_opening)
        self._logger.debug('target_pos {}'.format(target_pos))

        current_pos = self._fetch_current_positions()
        self._logger.debug('current_pos {}'.format(current_pos))

        cash = self._fetch_cash()
        collateral = cash
        for symbol in current_pos:
            collateral += current_pos[symbol]['pnl']
        self._logger.debug('cash {}'.format(cash))
        self._logger.debug('collateral {}'.format(collateral))

        self._cancel_all_orders()

        # create order
        margin_trade_type = 'day' # currently
        front_order_type = 'opening_market' if is_opening else 'closing_market'

        for symbol in set(target_pos.keys()) | set(current_pos.keys()):
            cur = current_pos[symbol]
            amount = target_pos[symbol] * self._leverage * collateral / cur['price'] - cur['pos']
            amount_unit = 100
            amount = round(amount / amount_unit) * amount_unit
            if amount == 0:
                continue

            if amount * current_pos[symbol] < 0:
                close_amount = min(np.abs(amount), np.abs(current_pos[symbol]))
                self._logger.info('create_order symbol {} amount {} close_amount {} front_order_type {}'.format(
                    symbol, amount, close_amount, front_order_type))
                self._client.create_order(
                    symbol=symbol,
                    side_int=np.sign(amount),
                    is_close_order=True,
                    margin_trade_type=margin_trade_type,
                    amount=close_amount,
                    front_order_type=front_order_type,
                )
                amount -= np.sign(amount) * close_amount
                if amount == 0:
                    continue

            self._logger.info('create_order symbol {} amount {} front_order_type {}'.format(
                symbol, amount, front_order_type))
            self._client.create_order(
                symbol=symbol,
                side_int=np.sign(amount),
                is_close_order=False,
                margin_trade_type=margin_trade_type,
                amount=np.abs(amount),
                front_order_type=front_order_type,
            )

    def _calc_target_positions(self, is_opening):
        now = time.time()
        day = 24 * 60 * 60

        exec_time = (now // day) * day + (day if is_opening else 6 * 60 * 60)

        df = self._alphapool_client.get_positions(
            min_timestamp=exec_time,
        )
        df = df.loc[df.index.get_level_values('timestamp') == pd.to_datetime(exec_time, unit='s', utc=True)]

        merged = defaultdict(float)
        positions = df.groupby('model_id')['positions'].nth(-1)
        for pos in positions:
            for symbol in pos:
                merged[symbol] += pos[symbol] / positions.shape[0]

        return merged

    def _fetch_current_positions(self):
        positions = self._client.fetch_positions()
        merged = defaultdict(dict)
        for pos in positions:
            symbol = pos['Symbol']
            side_int = 2 * int(pos['Side']) - 3
            merged[symbol] = merged[symbol] or {
                'pos': 0.0,
                'price': pos['CurrentPrice'],
                'pnl': 0.0,
            }
            merged[symbol]['pos'] += side_int * pos['LeavesQty']
            merged[symbol]['pnl'] += pos['ProfitLoss']
        return merged

    def _fetch_cash(self):
        wallet = self._client.fetch_margin()
        return wallet['StockAccountWallet']

    def _cancel_all_orders(self):
        orders = self._client.fetch_orders()
        for order in orders:
            if order['State'] != '5':
                self._logger.info('cancel_order {}'.format(order))
                self._client.cancel_order(order['ID'])
