import datetime
import re


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
    assert len(date_parts) == 4
    time = date_parts[1]
    year, month, day = time.split("-")

    # 將日期字串轉換為 datetime 對象
    dt = datetime.datetime(int(year), month_dict[month], int(day))

    return dt


def data_to_string_array(data: str) -> list[str]:
    data_list = data.split("\n")
    new_list = [item for item in data_list if item]
    return new_list

# def data_item_str_to_dic(item:str) -> dict[str]: