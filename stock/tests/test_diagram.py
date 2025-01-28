from pickle import FALSE

from src.diagram.kLine import convert2k_line_diagram, draw_k_line
from src.tables.initDataFrame import get_stock_data
import pytest

# SHOW_DIAGRAM = True
SHOW_DIAGRAM = False


@pytest.mark.skipif(SHOW_DIAGRAM is False, reason="do not need to show disgram")
def test_k_line():
    data = get_stock_data("2330")
    draw_k_line(convert2k_line_diagram(data))
