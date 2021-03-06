import psycopg2
import pandas as pds
from sqlalchemy import create_engine
import datetime
import time

import matplotlib.pyplot as plt
import matplotlib

# matplotlib.use("tkagg")


DB_LOGIN = ""


# Create an engine instance

alchemyEngine = create_engine(
    DB_LOGIN,
    pool_recycle=3600,
)


# Connect to PostgreSQL server

dbConnection = alchemyEngine.connect()


# Read data from PostgreSQL database table and load into a DataFrame instance

bids = pds.read_sql("select * from auction", dbConnection)


orderFills = pds.read_sql("select * from orderfill ", dbConnection)

treasuryDeposits = pds.read_sql("select * from coordinatortreasurydeposit", dbConnection)

volumeUSD = orderFills[["makerTokenFilledAmountUSD", "takerTokenFilledAmountUSD", "timestamp"]]

launchDate = datetime.datetime(2022, 4, 21)

volumeUSD = volumeUSD[volumeUSD["timestamp"] > datetime.datetime.timestamp(launchDate)]

datetimes = []
dailyVolume = []

day = launchDate
timestamp = datetime.datetime.timestamp(day)


### ROOK BID STUFF

launch_date = datetime.datetime(2022, 4, 21)
launch_timestamp = datetime.datetime.timestamp(launch_date)

# Read data from PostgreSQL database table and load into a DataFrame instance
auctions = pds.read_sql(
    'SELECT "auctionId", "auctionCreationTime", "user" FROM auction \
    WHERE "user" != \'null\' ',
    dbConnection,
)

bids = pds.read_sql(
    'SELECT bid."bidId", bid."auctionId", bid."rook_etherUnits", bidoutcome."txHash", bidoutcome."batchCount" FROM bid \
    LEFT JOIN (SELECT bidoutcome."txHash", bidoutcome."outcomeValue", bidoutcome."batchCount", bidoutcome."bidId" FROM bidoutcome) bidoutcome ON bidoutcome."bidId" =  bid."bidId"\
    WHERE bidoutcome."outcomeValue" > 0',
    dbConnection,
)

order_fills = pds.read_sql("SELECT * FROM orderfill", dbConnection)

auctions = auctions[auctions["auctionCreationTime"] > launch_timestamp]
order_fills = order_fills[order_fills["timestamp"] > launch_timestamp]

bid_volume_data = order_fills.join(bids.set_index("txHash"), on="txHash").dropna()

total_rook_bid_volume_USD = (
    bid_volume_data["rookPrice"].mul(bid_volume_data["rook_etherUnits"].div(bid_volume_data["batchCount"] ** 2)).sum()
)
total_trading_volume_USD = order_fills["takerTokenFilledAmountUSD"].sum()

print(f"total trading volume ($): \t{total_trading_volume_USD}")
print(f"total bid volume ($): \t\t{total_rook_bid_volume_USD}")
print(f"all time bid/volume ratio: \t{total_rook_bid_volume_USD / total_trading_volume_USD}")

bid_volume_data["correctedRookBidUSD"] = bid_volume_data["rookPrice"].mul(
    bid_volume_data["rook_etherUnits"].div(bid_volume_data["batchCount"] ** 2)
)

# USE THIS ONE FOR PLOTTING. correctedRookBidUSD is the value you want
bid_volume_data["Date"] = [datetime.datetime.fromtimestamp(timestamp) for timestamp in bid_volume_data["timestamp"]]


# print(f"Timestamp: {timestamp}")

while timestamp < datetime.datetime.timestamp(datetime.datetime.now()):

    dailyFills = volumeUSD[volumeUSD["timestamp"] > timestamp]

    dailyFills = dailyFills[dailyFills["timestamp"] <= datetime.datetime.timestamp(day + datetime.timedelta(days=1))]

    dailyVolume.append(dailyFills["makerTokenFilledAmountUSD"].sum())
    datetimes.append(day + datetime.timedelta(days=1))

    usdVoume = dailyFills["makerTokenFilledAmountUSD"].sum()

    # print(f"volume from {day} to {day + datetime.timedelta(days=1)}: {usdVoume}")

    day = day + datetime.timedelta(days=1)
    timestamp = datetime.datetime.timestamp(day)

bid_volume_data.set_index("Date", inplace=True)
dailyVolumeUSD = pds.DataFrame({"Date": datetimes, "volumeUSD": dailyVolume})
dailyVolumeUSD.set_index("Date", inplace=True)
revenue = pds.read_csv(
    "Daily_Supply-Side_Revenue_Vs._Protocol_Revenue_In_The_Past_180_Days._2022-06-29.csv", index_col="Date"
)

dailyVolumeUSD.index = pds.to_datetime(dailyVolumeUSD.index)
revenue.index = pds.to_datetime(revenue.index)
bid_volume_data.index = pds.to_datetime(bid_volume_data.index)

total_volume_USD = volumeUSD["makerTokenFilledAmountUSD"].sum()
total_supply_revenue = revenue["Protocol Revenue ($)"].sum()
total_protocol_revenue = revenue["Treasury Revenue ($)"].sum()

daily_volume_USD = pds.DataFrame(
    {"timestamp": volumeUSD["timestamp"], "volumeUSD": volumeUSD["makerTokenFilledAmountUSD"]}
)
daily_volume_USD["Date"] = [datetime.datetime.fromtimestamp(timestamp) for timestamp in daily_volume_USD["timestamp"]]
daily_volume_USD.set_index("Date", inplace=True)
daily_volume_USD.index = pds.to_datetime(daily_volume_USD.index)

revenue = revenue.resample("3D").sum()
daily_volume_USD = daily_volume_USD.resample("3D").sum()
bid_volume_data = bid_volume_data.resample("3D").sum()
revenue = revenue.cumsum()
daily_volume_USD = daily_volume_USD.cumsum()
bid_volume_data = bid_volume_data.cumsum()

print(daily_volume_USD)

fmt_str = "%d-%m"
daily_volume_USD.index = daily_volume_USD.index.strftime(fmt_str)
revenue.index = revenue.index.strftime(fmt_str)
bid_volume_data.index = bid_volume_data.index.strftime(fmt_str)

# bid_volume_data = bid_volume_data.loc[:, ['correctedRookBidUSD', 'makerTokenFilledAmountUSD']]

bid_volume_data["income_ratio"] = bid_volume_data["correctedRookBidUSD"] / daily_volume_USD["volumeUSD"]


fig = plt.figure()
subfigs = fig.subfigures(2, 1)

ax1 = subfigs[0].add_subplot(111)
ax2 = ax1.twinx()
daily_volume_USD.plot(kind="bar", ax=ax1, y=["volumeUSD"], color=["blue"])
bid_volume_data.plot(kind="bar", ax=ax2, y=["correctedRookBidUSD"], color=["red"])


# # revenue.plot(kind="bar", ax=ax2, color=["#ff7f0e", "#2ca02c"])
# bid_volume_data.correctedRookBidUSD.plot(kind="bar", ax=ax2, #color=["#ff7f0e", "#2ca02c"])

ax1.legend(loc="upper left")
ax2.legend(loc="upper right")

ax1.set_ylabel("Trading Volume ($)")
ax2.set_ylabel("ROOK bid volume ($)")

ax1.set_ylim(0, 300000000)
ax2.set_ylim(0, 500000)

# plt.ylim((10^6, 300*10^6))
# ax1.set_ylim(0, 0.002)
# ax2.set_ylim(0, 300000)

ax13 = subfigs[1].add_subplot(111, sharex=ax1)
ax13.get_shared_x_axes().join(ax13, ax2)
bid_volume_data.plot(kind="line", ax=ax13, y="income_ratio")
ax13.set_ylim(0, 0.002)
plt.show()

print(total_protocol_revenue)
print(total_supply_revenue)
print(total_volume_USD)
print(f"Protocol revenue to volume ratio: {total_supply_revenue / total_volume_USD}")
print(f"Treasury revenue to volume ratio: {total_protocol_revenue / total_volume_USD}")

print(bid_volume_data)


dbConnection.close()
