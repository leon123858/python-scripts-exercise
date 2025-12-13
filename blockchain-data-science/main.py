import pandas as pd

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