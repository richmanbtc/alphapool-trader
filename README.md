## alphasea-trade-bot

alphasea-trade-botは、
定期的に[alphasea-agent](https://github.com/alphasea-dapp/alphasea-agent)
からメタモデルポジションを取得し、仮想通貨取引所の無期限先物(Perpetual)のポジションを自動でリバランスするボットです

対応取引所

- FTX (PERP)
- Binance (USDT future)

## 準備

alphasea-trade-botの動作には、
[alphasea-agent](https://github.com/alphasea-dapp/alphasea-agent)
が必要です。リンク先の手順に従ってセットアップしてください。

## インストール

alphasea-trade-botリポジトリをクローンします。

```bash
git clone https://github.com/alphasea-dapp/alphasea-trade-bot.git
```

以降の作業はクローンしたディレクトリ内で行います。

## 動かし方

### .envファイル作成

以下のような内容の.envファイルをalphasea-trade-botディレクトリ直下に作ります。

#### **`.env`**
```text
ALPHASEA_AGENT_BASE_URL=http://[alphasea-agentのIPアドレス]:8070
CCXT_EXCHANGE=binance
CCXT_API_KEY=xxx
CCXT_API_SECRET=xxx
```

ALPHASEA_AGENT_BASE_URLにはalphasea-agentのURLを指定します。

CCXT_EXCHANGEにはccxtの取引所ID(ftx, binanceなど)を指定します。
CCXT_API_KEYとCCXT_API_SECRETには取引所のAPIキーとシークレットを指定します。
FTXの場合、CCXT_API_SUBACCOUNTでサブアカウントを指定できます。

### 起動

以下のコマンドを実行し、trade-botを起動します。

```bash
docker-compose up -d
```

以下のコマンドで、trade-botのログを確認できます。

```bash
docker-compose logs -f
```

以上で、セットアップは完了です。

## environment variables

|name|description|
|:-:|:-:|
|ALPHASEA_AGENT_BASE_URL|alphasea-agentのbase URL|
|CCXT_EXCHANGE|ccxtの取引所ID(ftx, binanceなど)を指定|
|CCXT_API_KEY|取引所APIキー|
|CCXT_API_SECRET|取引所APIシークレット|
|CCXT_API_SUBACCOUNT|サブアカウント名(optional)|

## 対応取引所の増やし方

ccxtを使って取引所間の差を吸収していますが、
一部のコードはccxtだけで吸収しきれないので、分岐を書いています。
分岐は"ftx"や"binance"で検索すると見つけられます。
そこに新しい取引所用の分岐を足せば追加できると思います。
プルリクを投げてください。

## Development

### test

alphasea-agentに依存。

```bash
docker-compose run --rm trade_bot bash scripts/test.sh
```
