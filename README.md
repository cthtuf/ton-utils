# This is a collection of scripts to work with TON
## Jetton Sender
### Description
Script for sending jettons from a source wallet to a list of destination wallets.

### Dependencies Installation
```shell
poetry install
```

### Usage
```shell
python jetton_sender.py [options]
```
#### Options:
- **--api_key**: TON Center API Key. You can also set it as environment variable `TON_CENTER_API_KEY`. Obtain it [here](https://t.me/tonapibot).
- **--jetton-address**: Address of the jetton.
- **--jetton-send-amount**: Amount of jettons to send.
- **--jetton-send-fee**: Fee for sending.
- --jetton-send-sleep: Pause between sends in seconds (default is 60).
- --source-wallet-version: Version of the source wallet (default is "v4r2").
- --source-wallet-mnemonic-file: File containing mnemonics of the source wallet (default is ".mnemonics").
- --destination-wallets-file: File with destination wallet addresses (default is ".wallets").

### Example
```shell
python jetton_sender.py --api_key YOUR_API_KEY --jetton-address YOUR_JETTON_ADDRESS --jetton-send-amount 100 --jetton-send-fee 0.04
```

### Files
- .mnemonics: File with 24 lines of mnemonics. Trim spaces on each line.
- .wallets: File with destination wallet addresses. One address per line. Trim spaces on each line.
