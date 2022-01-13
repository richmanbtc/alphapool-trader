import os
import ccxt
import time
from .agent_api import fetch_blended_prediction
from .utils import (
    create_ccxt_client,
    fetch_positions,
    fetch_tickers,
    fetch_collateral,
    symbol_to_ccxt_symbol,
    normalize_amount,
    round_to_execution_start_at
)
from .logger import create_logger

exchange = os.getenv('CCXT_EXCHANGE')
api_key = os.getenv('CCXT_API_KEY')
api_secret = os.getenv('CCXT_API_SECRET')
subaccount = os.getenv('CCXT_SUBACCOUNT')
leverage = float(os.getenv('ALPHASEA_LEVERAGE'))
agent_base_url = os.getenv('ALPHASEA_AGENT_BASE_URL')
log_level = os.getenv('ALPHASEA_LOG_LEVEL')


def rebalance_job():
    execution_start_at = round_to_execution_start_at(time.time())
    execution_time = 60 * 60
    execution_time_buffer = 5 * 60

    logger = create_logger(log_level)

    client = create_ccxt_client(
        exchange=exchange,
        api_key=api_key,
        api_secret=api_secret,
        subaccount=subaccount,
    )

    markets = {market['symbol']: market for market in client.fetch_markets()}
    collateral = fetch_collateral(client)
    logger.info('collateral {}'.format(collateral))

    # 初期ポジション取得
    df_initial = fetch_positions(client)
    df_initial['phase'] = 'initial'
    logger.debug('df_initial {}'.format(df_initial))

    # ターゲットポジション取得
    df_target = fetch_blended_prediction(
        agent_base_url=agent_base_url,
        execution_start_at=execution_start_at,
    )
    df_target.index = df_target.index.map(lambda x: symbol_to_ccxt_symbol(x, exchange=exchange))
    df_ticker = fetch_tickers(client)
    df_target = df_target.join(df_ticker[['close']], on='symbol', how='left')
    df_target['position'] = leverage * df_target['position'] * collateral / df_target['close']
    df_target['phase'] = 'target'
    logger.debug('df_target {}'.format(df_target))

    # 1時間かけてターゲットポジションへリバランス
    while time.time() < execution_start_at + execution_time + execution_time_buffer:
        time.sleep(10)

        try:
            df_current = fetch_positions(client)
            df_current['phase'] = 'current'
            logger.debug('df_current {}'.format(df_current))

            df_pos = pd.concat([
                df_initial,
                df_target,
                df_current,
            ])
            df_pos = df_pos.reset_index().pivot(index='phase', columns='symbol', values='position')
            df_pos = df_pos.fillna(0)
            df_pos = df_pos.loc[:, df_pos.abs().max(axis=0) > 0]  # drop all zero symbol
            logger.debug('df_pos {}'.format(df_pos))

            for symbol in df_pos.columns:
                initial = df_pos.loc['initial', symbol]
                target = df_pos.loc['target', symbol]
                current = df_pos.loc['current', symbol]

                t = (time.time() - execution_start_at) / execution_time
                t = np.clip(t, 0, 1)
                pos = (1 - t) * initial + t * target

                signed_amount = pos - current
                signed_amount = normalize_amount(
                    signed_amount,
                    price=prices[symbol],
                    market=markets[symbol]
                )

                if signed_amount == 0:
                    continue

                time.sleep(10)
                logger.info('create_order symbol {} signed_amount {}'.format(
                    symbol, signed_amount
                ))
                client.create_order(
                    symbol,
                    'market',
                    'sell' if signed_amount < 0 else 'buy',
                    np.abs(signed_amount),
                )
        except Exception as e:
            logger.error(e)
