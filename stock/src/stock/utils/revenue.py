import pandas as pd


def get_revenue_by_date_offset(
    data: pd.DataFrame, date_list: list[pd.Timestamp], offset: int
) -> float:
    price = 0.0
    revenue = 0.0
    buy_queue: list[int] = []
    pre_pay = 0.0

    if not date_list:
        raise ValueError("date is empty")
    if offset <= 0:
        raise ValueError("offset should be positive")

    for index, row in data.iterrows():
        cur_pay = row["price"]
        pre_pay = cur_pay
        buy_queue = [value - 1 for value in buy_queue]
        sell_count = buy_queue.count(0)
        buy_queue = [value for value in buy_queue if value != 0]
        revenue += sell_count * cur_pay

        if index in date_list:
            price += cur_pay
            buy_queue.append(offset)

    if buy_queue:
        revenue += pre_pay * len(buy_queue)

    return price / revenue


def get_revenue_by_line_offset(
    data: pd.DataFrame, data_name: str, offset: float
) -> float:
    price = 0.0
    revenue = 0.0
    hold_count = 0
    mean = data[data_name].mean()
    high_limit = mean + offset
    low_limit = mean - offset
    cur_price = 0.0

    for _, row in data.iterrows():
        cur_price = row["price"]
        cur_target = row[data_name]
        if pd.isna(cur_target):
            continue
        if cur_target < low_limit:
            price += cur_price
            hold_count += 1
        elif cur_target > high_limit and hold_count > 0:
            revenue += cur_price
            hold_count -= 1

    if hold_count > 0:
        revenue += cur_price * hold_count

    if price == 0.0 and revenue == 0.0:
        return -1.0

    return price / revenue
