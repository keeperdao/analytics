from time import sleep, time
import requests, json
from web3 import Web3
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
import os
from os.path import exists
from dotenv import load_dotenv
from functools import reduce
from multicall import Call, Multicall

load_dotenv()
INFURA_KEY = os.getenv("INFURA_KEY")

w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/{}".format(INFURA_KEY)))

HIDING_VAULT_NFT_ADDRESS = "0xE2aD581Fc01434ee426BB3F471C4cB0317Ee672E"
COMPOUND_TOKENS = json.load(open("ctokens.json"))
CTOKENS = {
    token: COMPOUND_TOKENS[token] for token in COMPOUND_TOKENS if token[0] == "c"
}
UNDERLYING_TOKENS = {
    token: COMPOUND_TOKENS[token] for token in COMPOUND_TOKENS if token[0] != "c"
}


def to_decimal(value, token):
    return value / (10 ** COMPOUND_TOKENS[token]["decimals"])


def to_address(value):
    address = f"0x{w3.toHex(value)[2:].zfill(40)}"
    return address


# Fetches the address of each HidingVaultNFT using tokenByIndex
def get_hv_addresses(numTokens):

    HidingVaultNFTAddress = HIDING_VAULT_NFT_ADDRESS

    calls = [
        Call(
            HidingVaultNFTAddress,
            ["tokenByIndex(uint256)(uint256)", i],
            [[i, to_address]],
        )
        for i in range(numTokens)
    ]
    multi = Multicall(calls, _w3=w3)
    result = multi()

    return [address for (index, address) in result.items()]


# Fetches the owner of each HidingVaultNFT
def get_hv_owners(vaultAddresses):

    HidingVaultNFTAddress = HIDING_VAULT_NFT_ADDRESS

    calls = [
        Call(
            HidingVaultNFTAddress,
            ["ownerOf(uint256)(address)", w3.toInt(hexstr=vault)],
            [[vault, None]],
        )
        for vault in vaultAddresses
    ]
    multi = Multicall(calls, _w3=w3)
    result = multi()

    return result


# Fetches compound_isUnderwritten status for each vaultAddress
def get_hv_underwritten_status(vaultAddresses):

    calls = [
        Call(vault, ["compound_isUnderwritten()(bool)"], [[vault, None]])
        for vault in vaultAddresses
    ]
    multi = Multicall(calls, _w3=w3)
    result = multi()

    return result


# Fetches compound_unhealth value for each vaultAddress
def get_hv_unhealth(vaultAddresses):

    calls = [
        Call(vault, ["compound_unhealth()(uint256)"], [[vault, None]])
        for vault in vaultAddresses
    ]
    multi = Multicall(calls, _w3=w3)
    result = multi()

    return result


# Fetches the token balances supplied to the Compound protocol by each HidingVaultNFT
def get_hv_supply_balances(vaultAddresses):

    calls = [
        Call(
            CTOKENS[cToken]["address"],
            ["balanceOfUnderlying(address)(uint256)", vault],
            [[f"{vault}:{cToken[1:]}", None]],
        )
        for cToken in CTOKENS
        for vault in vaultAddresses
    ]
    multi = Multicall(calls, _w3=w3)
    result = multi()

    # Filter out zero balances
    balances = {key: value for (key, value) in result.items()}  # if value > 0 }

    # Compile balances by vault address with this horrific reducer (whoever is reading this, I apologize)
    balances = reduce(
        lambda x, y: x
        | {
            y[0]: {y[1]: to_decimal(y[2], y[1])} | x[y[0]]
            if y[0] in x.keys()
            else {y[1]: to_decimal(y[2], y[1])}
        },
        map(lambda x: (x[0].split(":")[0], x[0].split(":")[1], x[1]), balances.items()),
        {},
    )

    return balances


# Fetches the token balances borrowed from the Compound protocol by each HidingVaultNFT
def get_hv_borrow_balances(vaultAddresses):

    calls = [
        Call(
            CTOKENS[cToken]["address"],
            ["borrowBalanceCurrent(address)(uint256)", vault],
            [[f"{vault}:{cToken[1:]}", None]],
        )
        for cToken in CTOKENS
        for vault in vaultAddresses
    ]
    multi = Multicall(calls, _w3=w3)
    result = multi()

    # Filter out zero balances
    balances = {key: value for (key, value) in result.items()}  # if value > 0 }

    # Compile balances by vault address with this horrific reducer (whoever is reading this, I apologize)
    balances = reduce(
        lambda x, y: x
        | {
            y[0]: {y[1]: to_decimal(y[2], y[1])} | x[y[0]]
            if y[0] in x.keys()
            else {y[1]: to_decimal(y[2], y[1])}
        },
        map(lambda x: (x[0].split(":")[0], x[0].split(":")[1], x[1]), balances.items()),
        {},
    )

    return balances


# Fetch usd token prices from coingecko
def fetch_token_prices():

    COINGECKO_ERC20_PRICE_URL = (
        "https://api.coingecko.com/api/v3/simple/token_price/ethereum"
    )
    COINGECKO_ETH_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

    payload = {
        "contract_addresses": (",").join(
            [
                COMPOUND_TOKENS[token]["address"].lower()
                for token in COMPOUND_TOKENS
                if token != "ETH"
            ]
        ),
        "vs_currencies": "usd",
    }

    r = requests.get(COINGECKO_ERC20_PRICE_URL, params=payload)
    response = r.json()

    usdPrices = {token: 0 for token in COMPOUND_TOKENS}
    for token in COMPOUND_TOKENS:
        if COMPOUND_TOKENS[token]["address"].lower() in response.keys():
            usdPrices[token] = response[COMPOUND_TOKENS[token]["address"].lower()][
                "usd"
            ]

    payload = {"ids": "ethereum", "vs_currencies": "usd"}

    r = requests.get(COINGECKO_ETH_PRICE_URL, params=payload)
    response = r.json()

    usdPrices["ETH"] = response["ethereum"]["usd"]

    return usdPrices


def get_all_vault_data():

    # Load HidingVaultNFT contract ABI
    address = HIDING_VAULT_NFT_ADDRESS
    abi = json.load(open("ABI/HidingVaultNFT.json"))
    HidingVaultNFT = w3.eth.contract(address=address, abi=abi)

    # Fetch latest block number and timestamp
    latestBlock = w3.eth.get_block("latest")
    latestBlockNumber = latestBlock.number
    latestBlockTimestamp = latestBlock.timestamp
    print("Latest Block: {}".format(latestBlockNumber))

    # Fetch total supply of HidingVaultNFT tokens
    numVaults = HidingVaultNFT.functions.totalSupply().call()
    print("HidingVaultNFT total supply: {}".format(numVaults))

    # Fetch addresses of each hiding vault
    vaultAddresses = get_hv_addresses(numVaults)

    # Fetch owner of each vault
    vaultOwners = get_hv_owners(vaultAddresses)
    numOwners = len(set(list(vaultOwners.values())))
    print("Total Hiding Vault owners: {}".format(numOwners))

    # Fetch underwritten status of each vault
    vaultUnderwritten = get_hv_underwritten_status(vaultAddresses)

    # Fetch health status of each vault
    vaultUnhealth = get_hv_unhealth(vaultAddresses)

    # Fetch underlying Compound supply and borrow balances of each vault
    vaultSupplyBalances = get_hv_supply_balances(vaultAddresses)
    vaultBorrowBalances = get_hv_borrow_balances(vaultAddresses)

    # Sum all supply and borow token balances for each asset
    compoundTokens = [token for token in UNDERLYING_TOKENS]

    totalSupply = {token: 0 for token in compoundTokens}
    totalBorrow = {token: 0 for token in compoundTokens}
    for token in compoundTokens:
        totalSupply[token] = reduce(
            lambda x, y: x + (y[1][token] if token in y[1].keys() else 0),
            vaultSupplyBalances.items(),
            0,
        )
        totalBorrow[token] = reduce(
            lambda x, y: x + (y[1][token] if token in y[1].keys() else 0),
            vaultBorrowBalances.items(),
            0,
        )

    # Fetch latest CoinGecko prices for Compound tokens
    usdPrices = fetch_token_prices()

    # Sum total USD supply and borrow balances
    totalSupplyUSD = sum(
        [totalSupply[token] * usdPrices[token] for token in compoundTokens]
    )
    totalBorrowUSD = sum(
        [totalBorrow[token] * usdPrices[token] for token in compoundTokens]
    )
    print("Total Supply Balance USD: {}".format(totalSupplyUSD))
    print("Total Borrow Balance USD: {}".format(totalBorrowUSD))

    # Sum USD supply and borrow balances for each vault
    vaultSupplyUSD = {
        vault: sum(
            [
                vaultSupplyBalances[vault][token] * usdPrices[token]
                for token in compoundTokens
            ]
        )
        for vault in vaultAddresses
    }
    vaultBorrowUSD = {
        vault: sum(
            [
                vaultBorrowBalances[vault][token] * usdPrices[token]
                for token in compoundTokens
            ]
        )
        for vault in vaultAddresses
    }

    vaultSummaries = {
        vault: {
            "owner": vaultOwners[vault],
            "isUnderwritten": vaultUnderwritten[vault],
            "unhealth": vaultUnhealth[vault],
            "supplyBalances": vaultSupplyBalances[vault],
            "borrowBalances": vaultBorrowBalances[vault],
        }
        for vault in vaultAddresses
    }

    vaultsData = {
        "blockUpdated": latestBlockNumber,
        "numVaults": numVaults,
        "numOwners": numOwners,
        "totalSuppliedAssets": totalSupply,
        "totalBorrowedAssets": totalBorrow,
        "totalSupplyUSD": totalSupplyUSD,
        "totalBorrowUSD": totalBorrowUSD,
        "vaults": vaultSummaries,
    }

    with open("hidingVaults.json", "w", encoding="utf-8") as f:
        json.dump(vaultsData, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    get_all_vault_data()
