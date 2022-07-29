import os
import requests
import json

from dotenv import load_dotenv

load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETHERSCAN_API_URL = "https://api.etherscan.io/api"


def fetch_abi(contract_address):

    payload = {
        "module": "contract",
        "action": "getabi",
        "address": contract_address,
        "apikey": ETHERSCAN_API_KEY,
    }

    r = requests.get(ETHERSCAN_API_URL, params=payload)
    response = r.json()

    abi = response['result']

    return abi
