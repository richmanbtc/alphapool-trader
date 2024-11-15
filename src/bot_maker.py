from collections import defaultdict
import dataclasses
import time
import traceback
from ccxt.base.errors import OrderNotFound
import numpy as np
import pandas as pd
from .utils import (
    fetch_positions,
    fetch_collateral,
    symbol_to_ccxt_symbol,
    ccxt_symbol_to_symbol,
    normalize_amount,
    set_leverage
)

# position and amount
# always one of these two
# internal: relative to collateral
# exchange: same as exchange. internal * collateral / price / contract_size

MAX_LEVERAGE = 10


class BotMaker:
    def __init__(self, client=None, logger=None, leverage=None,
                 alphapool_client=None, model_id=None, health_check_ping=None,
                 unit_pos_smoother=None, ccxt_account_type=None):
        self._client = client
        self._ccxt_account_type = ccxt_account_type
        self._logger = logger
        self._order_interval = 1
        self._loop_interval = 60
        self._leverage = leverage
        self._alphapool_client = alphapool_client
        self._model_id = model_id
        self._leverage_set = set()
        self._health_check_ping = health_check_ping
        self._unit_pos_smoother = unit_pos_smoother

        # cache
        self._df_positions = None

        # strategy
        self._positions = {}
        self._weights = {}
        self._limit_orders = []
        self._order_processed_rows = set()

        # exchange states
        self._exchange_positions = defaultdict(float)

    def run(self):
        initialized = False

        while True:
            try:
                if not initialized:
                    self._initialize()
                    initialized = True

                self._step()
                self._health_check_ping()
            except Exception as e:
                self._logger.error(e)
                self._logger.error(traceback.format_exc())

            self._remove_old_data()
            time.sleep(self._loop_interval)

    def _initialize(self):
        self._logger.info('initialized')

    def _step(self):
        self._logger.debug('_positions {}'.format(self._positions))
        self._logger.debug('_weights {}'.format(self._weights))
        self._logger.debug('_limit_orders {}'.format(self._limit_orders))
        self._logger.debug('_order_processed_rows {}'.format(self._order_processed_rows))
        self._logger.debug('_exchange_positions {}'.format(self._exchange_positions))

        self._sync_limit_orders_and_exchange_positions()

        collateral = fetch_collateral(self._client, self._ccxt_account_type)
        self._logger.info('collateral {}'.format(collateral))
        markets = {market['symbol']: fix_market(market, self._client.id)
                   for market in self._client.fetch_markets()}
        self._fetch_models(collateral, markets)

        target_positions = self._get_target_positions(collateral, markets)
        self._sync_taker_positions(target_positions)
        self._submit_limit_orders(markets)

    def _sync_limit_orders_and_exchange_positions(self):
        df_current_pos = fetch_positions(self._client)
        df_current_pos = df_current_pos.loc[df_current_pos['position'] != 0]
        position_changed = self._sync_limit_orders()
        if not position_changed:
            # Since the order has not been filled since the last order sync until now,
            # you can safely force sync the positions acquired during that time.
            self._force_sync_exchange_positions(df_current_pos)

    def _sync_limit_orders(self):
        self._logger.info('_sync_limit_orders')

        now = time.time()
        position_changed = False

        ccxt_symbols = set([self._symbol_to_ccxt_symbol(x.symbol) for x in self._limit_orders])
        self._logger.info('fetch_open_orders ccxt_symbols {}'.format(ccxt_symbols))
        exchange_orders = []
        for ccxt_symbol in ccxt_symbols:
            exchange_orders += self._client.fetch_open_orders(ccxt_symbol)

        for i in range(len(self._limit_orders))[::-1]:
            order = self._limit_orders[i]
            ccxt_symbol = self._symbol_to_ccxt_symbol(order.symbol)

            if order.exchange_order_id is None:
                self._logger.info('order not submitted. skip {}'.format(order))
                continue

            exchange_order = None
            for exchange_order2 in exchange_orders:
                if exchange_order2['id'] == order.exchange_order_id:
                    exchange_order = exchange_order2
                    exchange_orders.remove(exchange_order2)
                    break
            if exchange_order is None:
                try:
                    exchange_order = self._client.fetch_order(order.exchange_order_id, symbol=ccxt_symbol)
                except OrderNotFound as e:
                    self._logger.warn('order not found. remove {} {}'.format(order, e))
                    self._limit_orders.pop(i)
                    continue

            signed_executed = (exchange_order['filled'] - order.executed_amount) * order.side_int()
            self._exchange_positions[order.symbol] += signed_executed

            if signed_executed != 0:
                position_changed = True
                self._logger.info('order executed old local {} new exchange {}'.format(order, exchange_order))
            order.executed_amount = exchange_order['filled']
            status = exchange_order['status']

            if status == 'open' and order.expired(now):
                self._logger.info('order expired. cancel order {}'.format(order))
                self._client.cancel_order(order.exchange_order_id, symbol=ccxt_symbol)

            if status != 'open' and order.get_position(now) == 0:
                self._logger.info('order exited. remove {}'.format(order))
                self._limit_orders.pop(i)

        for exchange_order in exchange_orders:
            self._logger.info('cancel unknown order {}'.format(exchange_order['id']))
            self._client.cancel_order(exchange_order['id'], symbol=exchange_order['symbol'])

        return position_changed

    def _force_sync_exchange_positions(self, df_current_pos):
        self._logger.info('force sync exchange positions')
        self._logger.info('df_current_pos {}'.format(df_current_pos))
        self._exchange_positions = defaultdict(float)
        for ccxt_symbol in df_current_pos.index:
            self._exchange_positions[ccxt_symbol_to_symbol(ccxt_symbol)] = df_current_pos.loc[ccxt_symbol, 'position']

    def _get_positions(self, now):
        inactive_time = 24 * 60 * 60
        if self._df_positions is None:
            df = self._alphapool_client.get_positions(
                min_timestamp=int(now - inactive_time),
            )
        else:
            df = self._alphapool_client.get_positions(
                min_timestamp=int(now - 60 * 60),
            )
            df = pd.concat([self._df_positions, df])
            t = df.index.get_level_values('timestamp')
            df = df.loc[t >= pd.to_datetime(now - inactive_time, unit='s', utc=True)]
            df = df.loc[~df.index.duplicated(keep='last')]
            df = df.sort_index()

        self._df_positions = df.copy()
        return df

    def _fetch_models(self, collateral, markets):
        now = time.time()

        df = self._get_positions(now)

        if df.shape[0] == 0:
            self._logger.info('close all because df.shape[0] == 0')
            self._positions = {}
            self._weights = {}
            return

        df = df.loc[df.index.get_level_values('timestamp') <= pd.to_datetime(now, unit='s', utc=True)]
        df = df.reset_index()
        df = df.groupby('model_id').nth(-1)

        def skip_symbol_not_exit(symbol):
            ccxt_symbol = self._symbol_to_ccxt_symbol(symbol)
            if ccxt_symbol not in markets:
                self._logger.warn('symbol {} not exist. skip'.format(ccxt_symbol))
                return True
            return False

        if self._model_id in df.index:
            new_weights = df.loc[self._model_id, 'weights']
        else:
            new_weights = {}
        if self._weights != new_weights:
            self._logger.info('weight updated {}'.format(new_weights))
            self._weights = new_weights

        # process positions
        new_positions = {}
        for row in df.itertuples():
            model_id = row.Index
            new_positions[model_id] = {}
            for symbol in row.positions:
                if skip_symbol_not_exit(symbol):
                    continue
                new_positions[model_id][symbol] = row.positions[symbol]
        if self._positions != new_positions:
            self._logger.info('position updated {}'.format(new_positions))
            self._positions = new_positions

        # process orders
        limit_order_amounts = defaultdict(float)
        for row in df.itertuples():
            model_id = row.Index
            timestamp = row.timestamp
            if (timestamp, model_id) in self._order_processed_rows:
                continue
            self._order_processed_rows.add((timestamp, model_id))
            self._logger.info('process order row {} {}'.format(timestamp, model_id))

            if order_is_old(now, timestamp):
                self._logger.info('too old order. skip')
                continue

            for symbol in row.orders:
                if skip_symbol_not_exit(symbol):
                    continue
                for order in row.orders[symbol]:
                    weight = self._weights.get(model_id, 0.0)
                    key = (timestamp.timestamp(), symbol, order['price'], order['is_buy'], order['duration'])
                    unit_pos = collateral / order['price']
                    limit_order_amounts[key] += amount_to_exchange_amount(
                        amount=order['amount'] * weight,
                        leverage=self._leverage,
                        unit_pos=unit_pos,
                        market=markets[self._symbol_to_ccxt_symbol(symbol)]
                    )

        for key in limit_order_amounts:
            amount = limit_order_amounts[key]
            if amount == 0:
                continue
            self._logger.info('limit order added {} {}'.format(key, amount))
            self._limit_orders.append(Order(
                timestamp=key[0],
                symbol=key[1],
                price=key[2],
                amount=amount,
                is_buy=key[3],
                reduce_only=False,
                duration=key[4],
                executed_amount=0.0,
                exchange_order_id=None,
            ))

    def _sync_taker_positions(self, target_positions):
        now = time.time()
        self._logger.info('_sync_taker_positions')
        self._logger.info('target_positions {}'.format(target_positions))

        all_symbols = (set(self._exchange_positions.keys())
                       | set(target_positions.keys()))
        self._logger.debug('all_symbols {}'.format(all_symbols))

        for symbol in all_symbols:
            target_pos = target_positions[symbol]
            cur_pos = self._exchange_positions[symbol]

            if target_pos == 0 and cur_pos == 0:
                continue

            signed_amount = target_pos - cur_pos

            # use reduce_only to reduce instant leverage peak
            reduce_only = use_reduce_only(signed_amount=signed_amount, cur_pos=cur_pos, exchange=self._client.id)
            if reduce_only:
                signed_amount = np.sign(signed_amount) * min(np.abs(signed_amount), np.abs(cur_pos))

            for order in list(self._limit_orders):
                if not (order.symbol == symbol and order.price is None):
                    continue

                if order.exchange_order_id is None:
                    self._logger.info('remove old order {}'.format(order))
                    self._limit_orders.remove(order)
                else:
                    self._logger.info('cancel old order {}'.format(order))
                    ccxt_symbol = self._symbol_to_ccxt_symbol(order.symbol)
                    try:
                        self._client.cancel_order(order.exchange_order_id, symbol=ccxt_symbol)
                    except OrderNotFound as e:
                        self._logger.warn('order not found. probably already executed. skip {} {}'.format(order, e))

            self._limit_orders.append(Order(
                timestamp=now,
                symbol=symbol,
                price=None,
                amount=np.abs(signed_amount),
                is_buy=signed_amount > 0,
                reduce_only=reduce_only,
                duration=300,
                executed_amount=0.0,
                exchange_order_id=None,
            ))

    def _submit_limit_orders(self, markets):
        for i in range(len(self._limit_orders))[::-1]:
            order = self._limit_orders[i]

            if order.exchange_order_id is not None:
                continue

            ccxt_symbol = self._symbol_to_ccxt_symbol(order.symbol)
            res = self._create_order(
                market=markets[ccxt_symbol],
                signed_amount=order.side_int() * order.amount,
                price=order.price,
                reduce_only=order.reduce_only,
            )
            if res is None:
                self._logger.info('remove skipped order {}'.format(order))
                self._limit_orders.pop(i)
            else:
                order.exchange_order_id = res['id']

    def _create_order(self, market=None, signed_amount=None, price=None, reduce_only=False):
        time.sleep(self._order_interval)

        symbol = market['symbol']
        params = {}
        order_type = 'limit'

        use_bbo = price is None and self._client.id == 'binance'

        ob = self._client.fetch_order_book(symbol=symbol)
        best_ask = ob['asks'][0][0]
        best_bid = ob['bids'][0][0]

        if price is None:
            price = best_ask if signed_amount < 0 else best_bid
        else:
            if signed_amount < 0:
                price = max(best_ask, price)
            else:
                price = min(best_bid, price)

        signed_amount = normalize_amount(
            signed_amount,
            price=price,
            market=market,
            reduce_only=reduce_only,
        )
        if signed_amount == 0:
            self._logger.info('signed_amount is zero. skip')
            return None

        if self._client.id == 'binance':
            params['timeInForce'] = 'GTX'
            params['reduceOnly'] = 'true' if reduce_only else 'false'
            if use_bbo:
                params['priceMatch'] = 'QUEUE'
        elif self._client.id == 'okx':
            order_type = 'post_only'
            params['reduceOnly'] = 'true' if reduce_only else 'false'
        elif self._client.id == 'bybit':
            params['timeInForce'] = 'PostOnly'
            params['reduceOnly'] = reduce_only
            params['positionIdx'] = 0
        elif self._client.id == 'kucoinfutures':
            params['postOnly'] = True
            params['reduceOnly'] = reduce_only
            params['leverage'] = MAX_LEVERAGE
        else:
            raise Exception(f'set postonly and reduceonly, not implemented {self._client.id}')

        self._ensure_leverage(market, MAX_LEVERAGE)

        self._logger.info('create_order symbol {} signed_amount {} price {} params {}'.format(
            symbol, signed_amount, price, params
        ))
        amount = np.abs(signed_amount)
        if self._client.id == 'bitflyer':
            amount = '{:.8f}'.format(amount)
        res = self._client.create_order(
            symbol,
            order_type,
            'sell' if signed_amount < 0 else 'buy',
            amount,
            None if use_bbo else price,
            params
        )
        self._logger.info('order created {}'.format(res))
        return res

    def _ensure_leverage(self, market, leverage):
        skipped_exchanges = [
            'bitflyer',
        ]
        if self._client.id in skipped_exchanges:
            self._logger.info(f'{self._client.id} _ensure_leverage skip')
            return

        symbol = market['symbol']
        if symbol in self._leverage_set:
            return
        self._logger.info('set_leverage symbol {} leverage {}'.format(
            symbol, leverage
        ))
        set_leverage(self._client, market, leverage, logger=self._logger)
        self._leverage_set.add(symbol)

    def _remove_old_data(self):
        now = time.time()
        self._order_processed_rows = set(
            [x for x in self._order_processed_rows if not order_is_old(now, x[0])]
        )

    def _get_target_positions(self, collateral, markets):
        now = time.time()
        target_positions = defaultdict(float)
        for model_id in self._weights:
            positions = self._positions.get(model_id, {})
            for symbol in positions:
                target_positions[symbol] += self._weights[model_id] * positions[symbol]

        for symbol in target_positions:
            if target_positions[symbol] == 0:
                continue
            ticker = self._client.fetch_ticker(self._symbol_to_ccxt_symbol(symbol))

            unit_pos = collateral / ticker['last']
            unit_pos = self._unit_pos_smoother.step(symbol, unit_pos)

            target_positions[symbol] = amount_to_exchange_amount(
                amount=target_positions[symbol],
                leverage=self._leverage,
                unit_pos=unit_pos,
                market=markets[self._symbol_to_ccxt_symbol(symbol)]
            )

        for order in self._limit_orders:
            target_positions[order.symbol] += order.side_int() * order.get_position(now)
        return target_positions

    def _symbol_to_ccxt_symbol(self, symbol):
        return symbol_to_ccxt_symbol(symbol, self._client.id)


@dataclasses.dataclass
class Order:
    timestamp: float
    symbol: str
    price: float
    amount: float
    is_buy: bool
    reduce_only: bool
    duration: float
    executed_amount: float
    exchange_order_id: str

    def get_position(self, now):
        if self.price is None:
            return 0.0
        exit_duration = 60 * 60
        expire_at = self.timestamp + self.duration
        exit_at = expire_at + exit_duration
        if now <= expire_at:
            return self.executed_amount
        elif now <= exit_at:
            return self.executed_amount * (exit_at - now) / exit_duration
        return 0.0

    def expired(self, now):
        expire_at = self.timestamp + self.duration
        return now > expire_at

    def side_int(self):
        return 1 if self.is_buy else -1


def order_is_old(now, timestamp):
    return timestamp < pd.to_datetime(now - 300, unit='s', utc=True)


def amount_to_exchange_amount(amount, leverage, unit_pos, market):
    return amount * leverage * unit_pos / market['contractSize']


def fix_market(market, exchange):
    if exchange == 'bitflyer':
        market['limits']['amount']['min'] = 0.01
        market['precision'] = {'amount': 0.00000001, 'price': 1.0}
        market['contractSize'] = 1.0
    return market


def use_reduce_only(signed_amount, cur_pos, exchange):
    if exchange in ['bitflyer']:
        return False
    if np.abs(cur_pos) * 10 < np.abs(signed_amount):
        return False
    # https://stackoverflow.com/questions/58408054/typeerror-object-of-type-bool-is-not-json-serializable
    if signed_amount * cur_pos < 0:
        return True
    else:
        return False
