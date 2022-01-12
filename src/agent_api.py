from io import StringIO
import requests
import pandas as pd


def fetch_blended_prediction(agent_base_url=None, execution_start_at=None):
    url = agent_base_url + '/blended_prediction.csv?execution_start_at={}'.format(execution_start_at)
    r = requests.get(url)
    csv_str = r.content.decode('utf-8')
    df = pd.read_csv(StringIO(csv_str), dtype=str).set_index('symbol')
    return df
