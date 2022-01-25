## alphasea-trade-bot

alphasea-trade-botは、
[alphasea-agent](https://github.com/alphasea-dapp/alphasea-agent)
から毎日メタモデル予測結果を取得してリバランスするプログラムです。

対応取引所

- ftx (PERP)
- binance (USDT future)

## 動かし方

.envファイルを作り、以下を設定します。

#### **`.env`**
```text
CCXT_EXCHANGE=ftx
CCXT_API_KEY=xxx
CCXT_API_SECRET=xxx
CCXT_SUBACCOUNT=xxx
```

以下でリバランスボットを起動します。

```bash
docker-compose up -d
```


## Development

### test

alphasea-agentに依存。

```bash
docker-compose run --rm trade_bot bash scripts/test.sh
```
