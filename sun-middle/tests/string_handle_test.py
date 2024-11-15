import unittest

from utils.string_handle import HorizonsResultsReader, read_txt_file


class MyTestCase(unittest.TestCase):
    def test_read_file(self):
        ret = read_txt_file("./assets/horizons_results.txt")
        self.assertNotEqual(ret, "")

    def test_read_pd(self):
        ret = HorizonsResultsReader("./assets/horizons_results.txt")
        self.assertIsNotNone(ret.read())


if __name__ == "__main__":
    unittest.main()
