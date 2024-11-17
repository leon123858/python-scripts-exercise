import datetime
import re

import pandas as pd


def read_txt_file(file_path: str) -> str:
    """讀取指定路徑的 txt 檔案內容。

    Args:
      file_path: 檔案的路徑。

    Returns:
      一個包含檔案所有內容的字串。
    """

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    return content


def extract_soe_sections(content: str) -> list[str]:
    """從指定檔案中提取所有被 $$SOE 包圍的文字片段。

    Args:
      content: 檔案的內容。

    Returns:
      一個包含所有提取片段的列表。
    """

    # 將檔案內容轉換為字串
    text = str(content)
    # 使用正則表達式匹配 $$SOE 和 $$SOE 之間的內容
    pattern = r"\$\$SOE(.*?)\$\$EOE"
    matches = re.findall(pattern, text, re.DOTALL)

    return matches


def extract_col_sections(content: str) -> list[str]:
    # 使用正則表達式提取 CSV 欄位資訊
    pattern = r"Date__\(UT\)__HR:MN,([\s\S]*?)\n"
    match = re.search(pattern, content)
    # 如果找到匹配的內容
    if match:
        csv_columns = match.group(0).strip().split(",")
        # 清理欄位名稱，去除空白和多餘的逗號
        csv_columns = [col.strip() for col in csv_columns]
        # remove final empty
        assert csv_columns.pop() == ""
        return csv_columns
    else:
        return []


def convert_date(date_string: str) -> datetime.datetime:
    """將 A.D. 2024-Aug-26 00:00:00.0000 TDB 格式轉換為一般格式。

    Args:
        date_string: 待轉換的日期字串。

    Returns:
        轉換後的日期。
    """
    # 將月份英文縮寫轉換為數字
    month_dict = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }

    date_parts = date_string.split()
    assert len(date_parts) == 2
    time = date_parts[0]
    year, month, day = time.split("-")

    # 將日期字串轉換為 datetime 對象
    dt = datetime.datetime(int(year), month_dict[month], int(day))

    return dt


def data_to_string_array(data: str) -> list[list[str]]:
    data_list = [item for item in data.split("\n") if item]
    new_list: list[list[str]] = []
    for row in data_list:
        items = [item.strip() for item in row.split(",")]
        items.pop()
        new_list.append(items)

    return new_list


def generate_pandas(col: list[str], data: list[list[str]]) -> pd.DataFrame:
    df = pd.DataFrame(data, columns=col)
    return df


class HorizonsResultsReader:
    def __init__(self, file_path: str):
        self.data = pd.DataFrame()
        self.path = file_path

    def read(self) -> pd.DataFrame:
        raw_data = read_txt_file(self.path)
        raw_data_string = extract_soe_sections(raw_data).pop()
        data_col = extract_col_sections(raw_data)
        data_list = data_to_string_array(raw_data_string)
        pdFrames = generate_pandas(data_col, data_list)
        self.data = pdFrames
        return pdFrames
