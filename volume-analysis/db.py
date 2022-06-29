from numpy import inner
import psycopg2
import pandas as pds
from sqlalchemy import create_engine
import datetime
import time

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use( 'tkagg' )


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

print(f"Timestamp: {timestamp}")

while timestamp < datetime.datetime.timestamp(datetime.datetime.now()):

    dailyFills = volumeUSD[volumeUSD["timestamp"] > timestamp]

    dailyFills = dailyFills[dailyFills["timestamp"] <= datetime.datetime.timestamp(day + datetime.timedelta(days=1))]

    dailyVolume.append(dailyFills["makerTokenFilledAmountUSD"].sum())
    datetimes.append(day + datetime.timedelta(days=1))

    usdVoume = dailyFills["makerTokenFilledAmountUSD"].sum()

    # print(f"volume from {day} to {day + datetime.timedelta(days=1)}: {usdVoume}")

    day = day + datetime.timedelta(days=1)
    timestamp = datetime.datetime.timestamp(day)

dailyVolumeUSD = pds.DataFrame({"Date": datetimes, "volumeUSD": dailyVolume})
dailyVolumeUSD.set_index("Date", inplace=True)
revenue = pds.read_csv(
    "Daily_Supply-Side_Revenue_Vs._Protocol_Revenue_In_The_Past_180_Days._2022-06-29.csv", index_col="Date"
)

dailyVolumeUSD.index = pds.to_datetime(dailyVolumeUSD.index)
revenue.index = pds.to_datetime(revenue.index)

total_volume_USD = volumeUSD["makerTokenFilledAmountUSD"].sum()
total_supply_revenue = revenue["Protocol Revenue ($)"].sum()
total_protocol_revenue = revenue["Treasury Revenue ($)"].sum()

revenue = revenue.resample('3D').sum()
dailyVolumeUSD = dailyVolumeUSD.resample('3D').sum()
revenue = revenue.cumsum()
dailyVolumeUSD = dailyVolumeUSD.cumsum()

fmt_str = "%d-%m"
dailyVolumeUSD.index = dailyVolumeUSD.index.strftime(fmt_str)
revenue.index = revenue.index.strftime(fmt_str)

ax1 = dailyVolumeUSD.plot(kind="bar")
# plt.ylim((10^6, 300*10^6))
ax2 = ax1.twinx()
revenue.plot(kind="bar", ax=ax2, color=["#ff7f0e", "#2ca02c"])

ax2.set_ylim(0, 300000)
# ax2.set_ylim(0, 5000)

plt.show()

print(total_protocol_revenue)
print(total_supply_revenue)
print(total_volume_USD)
print(f"Protocol revenue to volume ratio: {total_supply_revenue / total_volume_USD}")
print(f"Treasury revenue to volume ratio: {total_protocol_revenue / total_volume_USD}")


##dataFrame.to_csv("hidingBookOrders.csv")
# pds.set_option("display.expand_frame_repr", False)
# Print the DataFrame
# print(dataFrame)
# Close the database connection

dbConnection.close()
