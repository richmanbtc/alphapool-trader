from collections import defaultdict
from enum import Enum
from io import StringIO
import time
import traceback
import numpy as np
import pandas as pd
from retry import retry
import requests


class Timing(Enum):
    OPENING = 0
    MORNING_CLOSING = (2 * 60 + 30) * 60
    AFTERNOON_OPENING = (3 * 60 + 30) * 60
    CLOSING = 6 * 60 * 60


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
            timing = self._sleep_until_next_loop()

            @retry(tries=3, delay=3, logger=self._logger)
            def retry_step():
                self._step(timing)

            try:
                retry_step()
                self._health_check_ping()
            except Exception as e:
                self._logger.error(e)
                self._logger.error(traceback.format_exc())

    def _sleep_until_next_loop(self):
        day = 24 * 60 * 60
        buffer = 30 * 60
        now = time.time()

        configs = (
            (Timing.MORNING_CLOSING.value - buffer, Timing.MORNING_CLOSING),
            (Timing.AFTERNOON_OPENING.value - buffer, Timing.AFTERNOON_OPENING),
            (Timing.CLOSING.value - buffer, Timing.CLOSING),
            (Timing.OPENING.value - buffer + day, Timing.OPENING),
            (Timing.MORNING_CLOSING.value - buffer + day, Timing.MORNING_CLOSING),
        )

        for x, y in configs:
            if now % day < x:
                next_loop = (now // day) * day + x
                timing = y
                break

        self._logger.info('sleep until {} {}'.format(
            pd.to_datetime(next_loop, unit='s', utc=True),
            timing
        ))
        while time.time() < next_loop:
            self._health_check_ping()
            time.sleep(60)
        return timing

    def _step(self, timing):
        self._logger.info('step timing {}'.format(timing))

        target_pos = self._calc_target_positions(timing)
        self._logger.debug('target_pos {}'.format(target_pos))

        current_pos = self._fetch_current_positions()
        self._logger.debug('current_pos {}'.format(current_pos))

        cash = self._fetch_cash()
        collateral = cash
        for symbol in current_pos:
            collateral += current_pos[symbol]['pnl']
        self._logger.debug('cash {}'.format(cash))
        self._logger.debug('collateral {}'.format(collateral))

        day_margin_symbols = _fetch_day_margin_symbols()
        self._logger.debug('day_margin_symbols {}'.format(day_margin_symbols))

        self._cancel_all_orders()

        # create order
        margin_trade_type = 'day' # currently
        front_order_type = {
            Timing.OPENING: 'opening_market',
            Timing.MORNING_CLOSING: 'morning_closing_market',
            Timing.AFTERNOON_OPENING: 'afternoon_opening_market',
            Timing.CLOSING: 'closing_market',
        }[timing]

        self._logger.debug('day margin not available symbols {}'.format((set(target_pos.keys()) | set(current_pos.keys())) - set(day_margin_symbols)))

        symbols = list((set(target_pos.keys()) | set(current_pos.keys())) & set(day_margin_symbols))
        for symbol_i, symbol in enumerate(symbols):
            self._health_check_ping()

            if symbol_i % 50 == 0:
                self._register_symbols(symbols[symbol_i:symbol_i + 50])

            board = self._client.fetch_board(symbol)
            price = board['PreviousClose']

            cur = current_pos[symbol]
            amount = target_pos[symbol] * self._leverage * collateral / price - cur['pos']
            ideal_amount = amount
            amount_unit = 100
            amount = round(amount / amount_unit) * amount_unit

            # reg = self._client.fetch_regulations(symbol)
            # amount = _apply_regulations(amount, reg)

            self._logger.debug('symbol {} ideal_amount {} amount {} price {}'.format(
                symbol, ideal_amount, amount, price))

            if amount == 0:
                continue

            if amount * cur['pos'] < 0:
                close_amount = min(np.abs(amount), np.abs(cur['pos']))
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

    def _calc_target_positions(self, timing):
        now = time.time()
        day = 24 * 60 * 60

        exec_time = (now // day) * day + timing.value + (day if timing == Timing.OPENING else 0)

        df = self._alphapool_client.get_positions(
            min_timestamp=(exec_time // day) * day,
        )
        df = df.loc[df.index.get_level_values('timestamp') <= pd.to_datetime(exec_time, unit='s', utc=True)]

        merged = defaultdict(float)
        positions = df.groupby('model_id')['positions'].nth(-1)
        for pos in positions:
            for symbol in pos:
                merged[symbol.replace('.T', '')] += pos[symbol] / positions.shape[0]

        return merged

    def _fetch_current_positions(self):
        positions = self._client.fetch_positions()
        merged = defaultdict(lambda: { 'pos': 0.0, 'pnl': 0.0 })
        for pos in positions:
            symbol = pos['Symbol']
            side_int = 2 * int(pos['Side']) - 3
            merged[symbol]['pos'] += side_int * pos['LeavesQty']
            if pos['ProfitLoss'] is not None:
                merged[symbol]['pnl'] += pos['ProfitLoss']
        return merged

    def _fetch_cash(self):
        wallet = self._client.fetch_wallet_margin()
        return wallet['MarginAccountWallet']

    def _cancel_all_orders(self):
        orders = self._client.fetch_orders()
        for order in orders:
            if int(order['State']) != 5:
                self._logger.info('cancel_order {}'.format(order))
                self._client.cancel_order(order['ID'])

    def _register_symbols(self, symbols):
        self._client.unregister_all()
        self._client.register(symbols)


def _apply_regulations(amount, reg):
    for r in reg['RegulationsInfo']:
        if int(r['Exchange']) not in [0, 1]:
            continue
        if int(r['Product']) not in [0, 2]:
            continue

        if int(r['Side']) in [0, 1]:
            amount = max(0, amount)
        if int(r['Side']) in [0, 2]:
            amount = min(0, amount)

    return amount


def _fetch_day_margin_symbols():
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
    url = 'https://kabu.com/pdf/Gmkpdf/shinyou/meigara_list.csv'
    req = requests.get(url, headers={ "User-Agent": ua })
    req.encoding = 'shift_jis'
    df = pd.read_csv(StringIO(req.text), skiprows=1)
    df = df.loc[df['種類'] == 'デイトレ']
    return df['銘柄コード'].astype(str).tolist()
