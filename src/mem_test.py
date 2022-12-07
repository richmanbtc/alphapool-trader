import json
import tracemalloc
import pandas as pd
import dataset
from alphapool import Client
import gc
from ctypes import cdll, CDLL

tracemalloc.start()

def test1():
    obj = json.loads('{"BTC": 0.1234}')

def test2():
    df = pd.DataFrame([{'a': json.loads('{"BTC": 0.1234}')}])
    df['a'] = df['a'].apply(lambda x: {} if pd.isnull(x) else x)
    df = df.set_index(["a"]).sort_index()

database_url = 'postgresql://postgres:password@host.docker.internal/postgres'
db = dataset.connect(database_url)
alphapool_client = Client(db)

def test3():
    df = alphapool_client.get_positions(
        min_timestamp=1,
    )

def test4():
    results = alphapool_client._table.find()
    results = list(results)
    df = pd.DataFrame(results)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, unit="s")
    df = df.drop(columns=['id'])
    df['orders'] = df['orders'].apply(lambda x: {} if pd.isnull(x) else x)
    # df = df.set_index(["timestamp"])
    df = df.set_index(["timestamp", "model_id"])
    df = df.sort_index()

for i in range(10):
    test4()
    print(tracemalloc.get_traced_memory())
    gc.collect()
    print(tracemalloc.get_traced_memory())

    for j in range(100):
        # test1()
        # test2()
        # test3()
        test4()
    gc.collect()
    # cdll.LoadLibrary("libc.so.6")
    # libc = CDLL("libc.so.6")
    # libc.malloc_trim(0)
    print(tracemalloc.get_traced_memory())
