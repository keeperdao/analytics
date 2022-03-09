# KeeperDAO analytics

Catch-all repository for any scripts/tools used to analyze on-chain data. `ninjaFills.py` and `hidingVaults.py` are some basic messy example scripts for scraping event logs and making static contract calls respectively. 

To set up running these basic scripts
- install [poetry](https://python-poetry.org/)
- run `poetry install` in the top level directory
- make a `.env` file with values for `INFURA_KEY` and `ETHERSCAN_API_KEY` (you will need to set up accounts for infura and etherscan)
- run `poetry shell` to spin up the virtualenv

