from time import sleep, time
import requests, json
from web3 import Web3
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
import os
from os.path import exists
from dotenv import load_dotenv

load_dotenv()

INFURA_KEY = os.getenv("INFURA_KEY")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

ETHERSCAN_API_BASE_URL = "https://api.etherscan.io/api"

w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/{}".format(INFURA_KEY)))

# Scrapes all ninja hiding book fill event logs and gas usage data from startBlock to present
def getAllNinjaOrderFills(startBlock, blockStep):

    zrxExchangeProxy = "0xDef1C0ded9bec7F1a1670819833240f027b25EfF"
    rfqOrderFilled = (
        "0x829fa99d94dc4636925b38632e625736a614c154d55006b7ab6bea979c210c32"
    )
    ninjaTakerAddress = "3d71d79c224998e608d03c5ec9b405e7a38505f0"

    latestBlockNumber = startBlock
    currentBlockNumber = w3.eth.get_block_number()

    orderFills = []

    while latestBlockNumber < currentBlockNumber:

        # Filter for only RFQOrderFilled event logs from the 0x exchange proxy
        rfqFilter = w3.eth.filter(
            {
                "fromBlock": latestBlockNumber,
                "toBlock": latestBlockNumber + blockStep,
                "address": zrxExchangeProxy,
                "topics": [rfqOrderFilled],
            }
        )

        zrxLogs = w3.eth.get_filter_logs(rfqFilter.filter_id)

        if len(zrxLogs):

            # Get only logs involving ninja's taker address
            ninjaLogs = [log for log in zrxLogs if ninjaTakerAddress in log["data"]]

            print(
                "Block {}-{}: Found {} 0x RFQOrderFilled events, {} by Ninja".format(
                    latestBlockNumber,
                    latestBlockNumber + blockStep,
                    len(zrxLogs),
                    len(ninjaLogs),
                )
            )

            # For each ninja log found, scrape the txn involving that log and get gas data
            for log in ninjaLogs:
                txnHash = log["transactionHash"]

                txn = w3.eth.get_transaction(txnHash)
                gasLimit = txn["gas"]
                gasPrice = txn["gasPrice"]
                blockNumber = txn["blockNumber"]

                txnReceipt = w3.eth.get_transaction_receipt(txnHash)
                gasUsed = txnReceipt["gasUsed"]

                block = w3.eth.get_block(blockNumber)
                timestamp = block["timestamp"]

                dataStr = log["data"][2:]
                data = [dataStr[i : i + 64] for i in range(0, len(dataStr), 64)]

                orderFills.append(
                    {
                        "txHash": txnHash.hex(),
                        "orderHash": "0x" + data[0],
                        "maker": "0x" + data[1][-40:],
                        "taker": "0x" + data[2][-40:],
                        "makerToken": "0x" + data[3][-40:],
                        "takerToken": "0x" + data[4][-40:],
                        "makerTokenFilledAmount": Web3.toInt(hexstr=data[5]),
                        "takerTokenFilledAmount": Web3.toInt(hexstr=data[6]),
                        "gasLimit": int(gasLimit),
                        "gasUsed": int(gasUsed),
                        "gasPrice": int(gasPrice),
                        "timestamp": timestamp,
                        "blockNumber": blockNumber,
                    }
                )

        latestBlockNumber += blockStep

        # sleep to avoid getting rate limited
        sleep(0.5)

    # Save all the order fill data in a pickle file
    print("Found {} total Ninja order fills".format(len(orderFills)))
    np.save("ninjaFills", np.array(orderFills), allow_pickle=True)


def plotNinjaGasUsage():
    gas_payload = {
        "module": "gastracker",
        "action": "gasoracle",
        "apikey": ETHERSCAN_API_KEY,
    }

    price_payload = {
        "module": "stats",
        "action": "ethprice",
        "apikey": ETHERSCAN_API_KEY,
    }

    ninjaFills = np.load("ninjaFills.npy", allow_pickle=True)
    gas = np.array([txn["gasUsed"] for txn in ninjaFills])

    print("{} total ninja fills\n".format(len(ninjaFills)))
    print("Mean gas used: {}".format(np.mean(gas)))
    print("Median gas used: {}".format(np.median(gas)))
    print("Max gas used: {}".format(np.max(gas)))
    print("Min gas used: {}".format(np.min(gas)))

    # Just a rough estimate of the "cutoffs" for 1/2/3+ leg transactions based on observation
    oneHop = gas[gas < 265000]
    twoHop = gas[(gas >= 265000) & (gas < 380000)]
    threeHop = gas[gas >= 380000]

    print("\n")
    print("1 leg txns: {}".format(len(oneHop)))
    print("2 leg txns: {}".format(len(twoHop)))
    print("3 leg txns: {}".format(len(threeHop)))

    mu1, std1 = norm.fit(oneHop)
    mu2, std2 = norm.fit(twoHop)
    mu3, std3 = norm.fit(threeHop)

    r = requests.get(ETHERSCAN_API_BASE_URL, params=gas_payload)
    response = r.json()
    currentGas = float(response["result"]["ProposeGasPrice"])

    r = requests.get(ETHERSCAN_API_BASE_URL, params=price_payload)
    response = r.json()
    ethUsd = float(response["result"]["ethusd"])

    NINJA_MARGIN_USD = 100

    print("\n")
    print("Current Gas Price: {} gwei".format(currentGas))
    print("Current ETH Price: {} usd".format(ethUsd))

    print("\n")
    print("Distribution 1 - mu = {} gas sigma = {} gas".format(mu1, std1))
    print("Distribution 2 - mu = {} gas sigma = {} gas".format(mu2, std2))
    print("Distribution 3 - mu = {} gas sigma = {} gas".format(mu3, std3))

    print("\n")
    print(
        "Distribution 1 - mu = {} eth sigma = {} eth".format(
            mu1 * currentGas / 1e9, std1 * currentGas / 1e9
        )
    )
    print(
        "Distribution 2 - mu = {} eth sigma = {} eth".format(
            mu2 * currentGas / 1e9, std2 * currentGas / 1e9
        )
    )
    print(
        "Distribution 3 - mu = {} eth sigma = {} eth".format(
            mu3 * currentGas / 1e9, std3 * currentGas / 1e9
        )
    )

    print("\n")
    print(
        "Distribution 1 - mu = {} usd sigma = {} usd".format(
            ethUsd * mu1 * currentGas / 1e9, ethUsd * std1 * currentGas / 1e9
        )
    )
    print(
        "Distribution 2 - mu = {} usd sigma = {} usd".format(
            ethUsd * mu2 * currentGas / 1e9, ethUsd * std2 * currentGas / 1e9
        )
    )
    print(
        "Distribution 3 - mu = {} usd sigma = {} usd".format(
            ethUsd * mu3 * currentGas / 1e9, ethUsd * std3 * currentGas / 1e9
        )
    )

    mu1USD = ethUsd * mu1 * currentGas / 1e9
    sigma1USD = ethUsd * std1 * currentGas / 1e9
    mu2USD = ethUsd * mu2 * currentGas / 1e9
    sigma2USD = ethUsd * std2 * currentGas / 1e9
    mu3USD = ethUsd * mu3 * currentGas / 1e9
    std3USD = ethUsd * std3 * currentGas / 1e9

    print(
        "Two hop 99%% fill margin:\t${}".format(
            mu1USD + 3 * sigma1USD + NINJA_MARGIN_USD
        )
    )
    print(
        "Three hop 99%% fill margin:\t${}".format(
            mu2USD + 3 * sigma2USD + NINJA_MARGIN_USD
        )
    )
    print(
        "Four hop 99%% fill margin:\t${}".format(
            mu3USD + 3 * std3USD + NINJA_MARGIN_USD
        )
    )

    pairs = {}
    hopsByPair = {}
    r = requests.get("https://hidingbook.keeperdao.com/api/v1/tokenList")
    response = r.json()

    tokens = response["result"]["tokens"]
    hbTokensByAddress = {token["address"]: token for token in tokens}

    for txn in ninjaFills:
        hash = txn["txHash"]
        makerTokenAddress = txn["makerToken"]
        takerTokenAddress = txn["takerToken"]

        if (
            makerTokenAddress in hbTokensByAddress.keys()
            and takerTokenAddress in hbTokensByAddress.keys()
        ):
            makerToken = hbTokensByAddress[makerTokenAddress]["symbol"]
            takerToken = hbTokensByAddress[takerTokenAddress]["symbol"]
            gasUsed = txn["gasUsed"]
            # print('hash: {} makerToken:\t{}\t takerToken:\t{}\t gasUsed: {}'.format(hash, makerToken, takerToken, gasUsed))
            hops = 0
            if gasUsed < 265000:
                hops = 2
            elif gasUsed >= 265000 and gasUsed < 380000:
                hops = 3
            else:
                hops = 4

            if hash not in pairs.keys():
                pairs[hash] = {
                    "makerToken": makerToken,
                    "takerToken": takerToken,
                    "gasUsed": gasUsed,
                    "hops": hops,
                }

            token1 = makerToken if makerToken > takerToken else takerToken
            token2 = makerToken if makerToken < takerToken else takerToken

            pair = token1 + "/" + token2
            pait = makerToken + "/" + takerToken

            if pair not in hopsByPair.keys():
                hopArr = [0, 0, 0]
                hopsByPair[pair] = hopArr

            hopsByPair[pair][hops - 2] += 1

    for pair in hopsByPair:
        print("{}:\t\t{}".format(pair, hopsByPair[pair]))

    print("Num Pairs: {}".format(len(hopsByPair.keys())))

    json_hops = json.dumps(hopsByPair)
    with open("hops.json", "w") as file:
        file.write(json_hops)

    plt.hist(gas, bins=200)
    plt.xlabel("Gas Used")
    plt.ylabel("Frequency")

    xmin, xmax = plt.xlim()
    x1 = np.linspace(mu1 - 5 * std1, mu1 + 5 * std1, 100)
    x2 = np.linspace(mu2 - 5 * std2, mu2 + 5 * std2, 100)
    x3 = np.linspace(mu3 - 5 * std3, mu3 + 5 * std3, 100)
    p1 = np.array(norm.pdf(x1, mu1, std1)) * 10000000
    p2 = np.array(norm.pdf(x2, mu2, std2)) * 10000000
    p3 = np.array(norm.pdf(x3, mu3, std3)) * 10000000
    plt.plot(x1, p1, "b", linewidth=2, label="one leg")
    plt.plot(x2, p2, "r", linewidth=2, label="two leg")
    plt.plot(x3, p3, "g", linewidth=2, label="three leg")
    plt.legend()
    plt.show()

    """rookWeth = []

    for txn in ninjaFills:
        hash = txn["txHash"]
        makerTokenAddress = txn["makerToken"]
        takerTokenAddress = txn["takerToken"]
        if (
            makerTokenAddress in hbTokensByAddress.keys()
            and takerTokenAddress in hbTokensByAddress.keys()
        ):
            makerToken = hbTokensByAddress[makerTokenAddress]["symbol"]
            takerToken = hbTokensByAddress[takerTokenAddress]["symbol"]

            if makerToken == "ROOK" and takerToken == "WETH":
                rookWeth.append(txn)

    print("NUMBER OF ROOK/WETH TXNS: {}".format(len(rookWeth)))

    rookWethMakerAmount = [txn["makerTokenFilledAmount"] / 1e18 for txn in rookWeth]
    rookWethGasUsed = [txn["gasUsed"] for txn in rookWeth]

    txns = [txn["makerTokenFilledAmount"] / 1e18 for txn in rookWeth]

    plt.scatter(rookWethMakerAmount, rookWethGasUsed)
    plt.show()"""


if __name__ == "__main__":

    if exists("ninjaFills.npy"):
        plotNinjaGasUsage()
    else:
        getAllNinjaOrderFills(startBlock=13000000, blockStep=5000)
