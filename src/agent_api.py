from io import StringIO
import requests
import pandas as pd


def fetch_target_positions(agent_base_url=None, timestamp=None):
    tournament_id = 'crypto_daily'
    url = '{}/target_positions.csv?tournament_id={}&timestamp={}'.format(
        agent_base_url,
        tournament_id,
        int(timestamp),
    )
    r = requests.get(url)
    csv_str = r.content.decode('utf-8')
    df = pd.read_csv(StringIO(csv_str), dtype=str).set_index('symbol')
    df['position'] = df['position'].astype(float)
    return df
