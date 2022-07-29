import os
from unicodedata import decimal
import requests
import json
from dotenv import load_dotenv

from web3 import Web3

from util.addresses import addresses
from util.contracts import fetch_abi

load_dotenv()
INFURA_KEY = os.getenv("INFURA_KEY")


class RookSupply:

    def __init__(self):
        print('Initializing web3')
        self.web3 = Web3(Web3.HTTPProvider(
            "https://mainnet.infura.io/v3/{}".format(INFURA_KEY)))

        print('Fetching ROOK ABI')
        rook_address = addresses.rook
        rook_abi = fetch_abi(rook_address)
        rook_contract = self.web3.eth.contract(
            address=rook_address, abi=rook_abi)
        decimals = 10 ** rook_contract.functions.decimals().call()

        # Fetch ROOK balances
        print('Fetching ROOK supply balances')
        total_supply = rook_contract.functions.totalSupply().call()
        treasury = rook_contract.functions.balanceOf(
            addresses.treasury).call()
        strategic_reserves = rook_contract.functions.balanceOf(
            addresses.strategic_reserves).call()
        staked = rook_contract.functions.balanceOf(
            addresses.liquidity_pool_v4).call()

        # Set initial ROOK balances
        self.total_supply = total_supply / decimals
        self.treasury = treasury / decimals
        self.strategic_reserves = strategic_reserves / decimals
        self.staked = staked / decimals
        self.burned = 0
        self.unclaimed = 0

    def get_circulating_supply(self):
        return self.total_supply - self.treasury - self.strategic_reserves - self.burned - self.unclaimed
