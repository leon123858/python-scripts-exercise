import pandas as pd


def get_revenue_by_date_offset(
    data: pd.DataFrame, date_list: list[pd.Timestamp], offset: int
) -> float:
    price = 0.0
    revenue = 0.0
    buy_queue: list[int] = []
    pre_pay = 0.0
    if len(date_list) == 0:
        raise ValueError("date is empty")

    for index, row in data.iterrows():
        row = data.loc[index]
        cur_pay = row["price"]
        pre_pay = cur_pay
        buy_queue = [v - 1 for v in buy_queue]
        count = buy_queue.count(0)
        buy_queue = list(filter(lambda x: x != 0, buy_queue))
        revenue += count * cur_pay
        if index in date_list:
            price += cur_pay
            buy_queue.append(offset)

    if len(buy_queue) > 0:
        revenue += pre_pay * len(buy_queue)

    return price / revenue
