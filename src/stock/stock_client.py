import requests
import time
from ccxt_rate_limiter.rate_limiter import RateLimiter


# margin trading
class StockClient:
    def __init__(self, api_key, api_password, api_base_url, is_corp):
        self._api_key = api_key
        self._api_password = api_password
        self._api_base_url = api_base_url
        self._is_corp = is_corp
        self._rate_limiter = RateLimiter(period_sec=0.3, count=1)

    def fetch_wallet_cash(self):
        return self._request('/wallet/cash', 'get')

    def fetch_wallet_margin(self):
        return self._request('/wallet/margin', 'get')

    def fetch_orders(self):
        return self._request('/orders', 'get', { 'product': '2' })

    def fetch_positions(self):
        return self._request('/positions', 'get', { 'product': '2' })

    def create_order(self, symbol, side_int, is_close_order, margin_trade_type, amount,
                     front_order_type):
        return self._request('/sendorder', 'post', {
            'Password': self._api_password,
            'Symbol': symbol,
            'Exchange': 1,
            'SecurityType': 1,
            'Side': '1' if side_int < 0 else '2',
            'CashMargin': 3 if is_close_order else 2,
            'MarginTradeType': {
                'system': 1,
                'general': 2,
                'day': 3,
            }[margin_trade_type],
            'DelivType': 2 if is_close_order else 0,
            'AccountType': 12 if self._is_corp else 4,
            'Qty': amount,
            'ClosePositionOrder': 0,
            'FrontOrderType': {
                'opening_market': 13,
                'closing_market': 16,
            }[front_order_type],
            'Price': 0,
            'ExpireDay': 0,
        })

    def cancel_order(self, order_id):
        return self._request('/cancelorder', 'put', {
            'Password': self._api_password,
            'OrderId': order_id,
        })

    def _fetch_token(self):
        return self._request('/token', 'get', { 'APIPassword': self._api_key })

    def _request(self, path, method, options):
        url = '{}{}'.format(self.api_base_url, path)
        headers = {
            'Content-Type': 'application/json',
        }
        if path != '/token':
            if not self._token_exists():
                self._api_token = self._fetch_token()['Token']
                self._api_token_fetched_at = time.time()
            headers['X-API-KEY'] = self._api_token
        self._rate_limiter.rate_limit()
        res = requests.request(url, method=method, json=options, headers=headers)
        return res.json()

    def _token_exists(self):
        if not hasattr(self, '_api_token'):
            return False
        day = 24 * 60 * 60
        return time.time() // day == self._api_token_fetched_at // day
