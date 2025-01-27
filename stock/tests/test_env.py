import twstock


def test_stock_crawler_lib():
    stock = twstock.Stock("2330")
    assert stock.sid == "2330"
    assert len(stock.date) == 31
    assert len(stock.price) == 31
    assert len(stock.high) == 31
