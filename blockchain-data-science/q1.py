import pandas as pd

# SELECT token_address, COUNT(*) FROM `bigquery-public-data.crypto_ethereum.token_transfers` WHERE (TIMESTAMP_TRUNC(block_timestamp, DAY) > TIMESTAMP("2025-11-01") AND TIMESTAMP_TRUNC(block_timestamp, DAY) < TIMESTAMP("2025-12-11")) group by token_address

# read data.json
df = pd.read_json('data.json')
df.rename(columns={'f0_': 'cnt'}, inplace=True)
print(df.head())

# sort with cnt col
df.sort_values('cnt', ascending=False, inplace=True)
print(df.head(10))

total_count = df['cnt'].sum()
df['percentage'] = (df['cnt'] / total_count) * 100

print(df.head(10))