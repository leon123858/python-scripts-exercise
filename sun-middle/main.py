from utils.string_handle import data_to_string_array, extract_soe_sections
from utils.string_handle_test import read_txt_file


def main():
    raw_data = read_txt_file("./assets/horizons_results.txt")
    raw_data_string = extract_soe_sections(raw_data).pop()
    data_list = data_to_string_array(raw_data_string)
    for v in data_list:
        print(v)

if __name__ == "__main__":
    main()
