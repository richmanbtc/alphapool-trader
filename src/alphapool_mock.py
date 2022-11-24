import time
import pandas as pd


class MockClient:
    def __init__(self):
        pass

    def get_positions(self, tournament=None, min_timestamp=None):
        t = (int(time.time()) // 300) * 300
        df = pd.DataFrame([
            {
                'model_id': 'model1',
                'timestamp': t,
                'p.BTC': 1.0,
            }, {
                'model_id': 'mock',
                'timestamp': t,
                'w.model1': 1.0,
            }
        ])
        df['timestamp'] = pd.to_datetime(df["timestamp"], utc=True, unit='s')
        df = df.set_index(["model_id", "timestamp"]).sort_index()

        return df
