import time
import schedule
from .rebalance import rebalance_job

schedule.every().day.at('00:30').do(rebalance_job)

while True:
    schedule.run_pending()
    time.sleep(1)
