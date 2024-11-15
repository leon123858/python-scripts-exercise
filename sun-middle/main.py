from utils.string_handle import HorizonsResultsReader


def main():
    print(HorizonsResultsReader("./assets/horizons_results.txt").read())


if __name__ == "__main__":
    main()
