TODO

## binance post only error

- Many post only errors occur only with binance. It doesn't happen much with okx or bybit.
- The price unit of linkusdt is the same on these exchanges.
- Post only is enabled in bybit and okx
- I don't know the cause, but try using bbo only on binance.

## bybit position mode

Prior to v0.0.32, the position mode was set for each symbol using the API at startup, but after that, it was controlled by the bybit system default. Make sure the system default is one-way

https://bybit-exchange.github.io/docs/v5/position/position-mode

## pandas memory leak

see src/mem_test.py

- 1.5.0: leak
- 1.5.1, 1.5.2: fixed

## ubuntu desktop setup

- google compute engine
- ubuntu 20.04

```bash
sudo apt update
sudo apt -y upgrade
sudo apt -y install ubuntu-desktop xrdp
sudo systemctl enable xrdp
sudo systemctl start xrdp
sudo systemctl status xrdp
sudo adduser test
```

ssh tunnel 3389

```
gcloud compute ssh --zone zone-name instance-name --project project-name -- -NL 63389:localhost:3389
```

remote desktop connect to localhost:63389 with test user
