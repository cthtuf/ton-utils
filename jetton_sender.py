import typing as t

import argparse
import asyncio
import logging
import os
from enum import Enum
from time import sleep

from tenacity import (
    after_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)
from TonTools import (
    GetMethodError,
    Jetton,
    TonCenterClient,
    TonCenterClientError,
    Wallet,
)

logger = logging.getLogger("jetton_sender")


class WalletState(str, Enum):
    active = "active"
    inactive = "inactive"
    notinit = "notinit"


async def setup() -> t.Tuple[argparse.Namespace, list[str], list[str]]:
    parser = argparse.ArgumentParser(description="Send jettons from source wallet to destination wallets.")
    parser.add_argument(
        "--api-key",
        type=str,
        required=False,
        default=os.environ.get("TON_CENTER_API_KEY"),
        help="TON Center API Key. Get it from https://t.me/tonapibot",
    )
    parser.add_argument("--jetton-address", type=str, help="Jetton address", required=True)
    parser.add_argument("--jetton-send-amount", type=int, help="Amount of jettons to send", required=True)
    parser.add_argument("--jetton-send-fee", type=float, help="Fee", required=True)
    parser.add_argument(
        "--jetton-send-sleep",
        type=int,
        default=60,
        help="Sleep seconds between sends",
        required=False,
    )
    parser.add_argument("--source-wallet-version", type=str, default="v4r2", required=False)
    parser.add_argument(
        "--source-wallet-mnemonic-file",
        type=str,
        default=".mnemonics",
        help="File with 24 lines of mnemonic. Trim spaces on each line.",
        required=False,
    )
    parser.add_argument(
        "--destination-wallets-file",
        type=str,
        default=".wallets",
        required=False,
        help="File with destination wallets addresses. One address per line. Trim spaces on each line.",
    )
    args = parser.parse_args()

    try:
        with open(args.source_wallet_mnemonic_file) as swmf:
            source_wallet_mnemonic = [s.strip() for s in swmf.readlines()]
    except FileNotFoundError:
        logger.error("Wallet mnemonic file not found: %s", args.source_wallet_mnemonic_file)
        exit(2)

    try:
        with open(args.destination_wallets_file) as dwf:
            destination_wallets = [w.strip() for w in dwf.readlines()]
    except FileNotFoundError:
        logger.error("Destination wallets file not found: %s", args.destination_wallets_file)
        exit(2)

    return args, source_wallet_mnemonic, destination_wallets


@retry(
    stop=stop_after_attempt(int(os.getenv("RETRIEVE_RETRY_ATTEMPTS", 5))),
    wait=wait_fixed(int(os.getenv("RETRIEVE_RETRY_WAIT", 5))),
    retry=retry_if_exception_type(TonCenterClientError),
    after=after_log(logger, logging.INFO),
    reraise=True,
)
async def get_jetton(client: TonCenterClient, jetton_address: str) -> Jetton:
    jetton = Jetton(jetton_address, provider=client)
    await jetton.update()
    logger.info(jetton)

    return jetton


@retry(
    stop=stop_after_attempt(int(os.getenv("RETRIEVE_RETRY_ATTEMPTS", 5))),
    wait=wait_fixed(int(os.getenv("RETRIEVE_RETRY_WAIT", 5))),
    retry=retry_if_exception_type(TonCenterClientError),
    after=after_log(logger, logging.INFO),
    reraise=True,
)
async def get_wallet(client: TonCenterClient, mnemonics: list[str], wallet_version: str) -> t.Tuple[Wallet, str]:
    wallet = Wallet(provider=client, mnemonics=mnemonics, version=wallet_version)
    state = await wallet.get_state()
    logger.info("Source wallet state: %s", state)

    return wallet, state


@retry(
    stop=stop_after_attempt(int(os.getenv("SEND_RETRY_ATTEMPTS", 5))),
    wait=wait_fixed(int(os.getenv("SEND_RETRY_WAIT", 5))),
    retry=retry_if_exception_type(TonCenterClientError),
    after=after_log(logger, logging.INFO),
)
async def send_jetton(
    source_wallet: Wallet,
    destination_wallet: str,
    jetton: Jetton,
    amount: int,
    fee: float,
    sleep_seconds: int,
) -> None:
    try:
        api_response_code = await source_wallet.transfer_jetton(
            destination_address=destination_wallet,
            jetton_master_address=jetton.address,
            jettons_amount=amount,
            fee=fee,
        )
        logger.info("Jetton sent to wallet: %s with code %s", destination_wallet, api_response_code)
        sleep(sleep_seconds)
    except GetMethodError as gme:
        logger.error("Get method error for wallet: %s, error: %s", destination_wallet, str(gme))
    except BaseException as exc:
        logger.error("Cannot send jetton for wallet: %s, error: %s", destination_wallet, str(exc))
        raise


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args, source_wallet_mnemonic, destination_wallets = await setup()

    try:
        client = TonCenterClient(key=args.api_key)
        jetton = await get_jetton(client, args.jetton_address)
        source_wallet, source_wallet_state = await get_wallet(
            client,
            source_wallet_mnemonic,
            args.source_wallet_version,
        )
    except TonCenterClientError:
        logger.exception("Cannot get jetton or wallet.")
        exit(3)

    if source_wallet_state != WalletState.active:
        logger.error(
            "Source wallet %s is not active. Cannot use it for send jettons.",
            source_wallet.address,
        )
        exit(4)

    for destination_wallet in destination_wallets:
        await send_jetton(
            source_wallet=source_wallet,
            destination_wallet=destination_wallet,
            jetton=jetton,
            amount=args.jetton_send_amount,
            fee=args.jetton_send_fee,
            sleep_seconds=args.jetton_send_sleep,
        )


if __name__ == "__main__":
    asyncio.run(main())
