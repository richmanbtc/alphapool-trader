import time
import pandas as pd


class MockClient:
    def __init__(self):
        pass

    def get_positions(self, min_timestamp=None):
        t = (int(time.time()) // 300) * 300
        df = pd.DataFrame([
            {
                'model_id': 'model1',
                'timestamp': t,
                'positions': {
                    'BTC': 1.0
                },
                'weights': {},
                'orders': {}
            }, {
                'model_id': 'mock',
                'timestamp': t,
                'positions': {},
                'weights': {
                    'model1': 1.0
                },
                'orders': {}
            }
        ])
        df['timestamp'] = pd.to_datetime(df["timestamp"], utc=True, unit='s')
        df = df.set_index(['timestamp', 'model_id']).sort_index()

        return df
