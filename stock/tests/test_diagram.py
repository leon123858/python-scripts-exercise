from pickle import FALSE

from src.diagram.kLine import convert2k_line_diagram, draw_k_line
from src.diagram.line import draw_rsi_line
from src.events.events import get_event_line
from src.events.lines import RSILine
from src.tables.initDataFrame import get_stock_data
import pytest

from src.utils.revenue import get_revenue_by_line_offset

# SHOW_DIAGRAM = True
SHOW_DIAGRAM = False


@pytest.mark.skipif(SHOW_DIAGRAM is False, reason="do not need to show disgram")
def test_k_line():
    data = get_stock_data("2330")
    plt = draw_k_line(convert2k_line_diagram(data))
    plt.show()


@pytest.mark.skipif(SHOW_DIAGRAM is False, reason="do not need to show disgram")
def test_rsi_line():
    data = get_stock_data("2330")
    strategy = RSILine()
    get_event_line(data, strategy, 14)
    draw_rsi_line(data)

    for i in range(1, 25):
        print(get_revenue_by_line_offset(data, "rsi", i))
