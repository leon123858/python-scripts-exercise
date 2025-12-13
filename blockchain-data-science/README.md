# Blockchain Data Science

## ref

https://decert.me/tutorial/MasteringChainAnalytics/

## What will i do

i will try to do same analysis in tutorial, but using GCP blockchain analytics tools.

## questions

### q1:

```
SELECT token_address, COUNT(*) FROM `bigquery-public-data.crypto_ethereum.token_transfers` WHERE (TIMESTAMP_TRUNC(block_timestamp, DAY) > TIMESTAMP("2025-11-01") AND TIMESTAMP_TRUNC(block_timestamp, DAY) < TIMESTAMP("2025-12-11")) group by token_address
```

### q2:

```
SELECT
  block_timestamp AS block_time,
  topics[SAFE_OFFSET(1)] AS topic1,
  topics[SAFE_OFFSET(2)] AS topic2,
  topics[SAFE_OFFSET(3)] AS topic3,
  transaction_hash AS tx_hash
FROM
  `bigquery-public-data.crypto_ethereum.logs`
WHERE
  address = LOWER('0x1F98431c8aD98523631AE4a59f267346ea31F984')
  AND topics[SAFE_OFFSET(0)] = LOWER('0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118')
  AND (DATE(block_timestamp) >= '2025-11-1' AND DATE(block_timestamp) < '2025-12-1')
```