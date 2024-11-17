import os
import unittest

import matplotlib.pyplot as plt
import numpy as np

from services.sky_observer import SkyObserver, draw_polar
from utils.string_handle import HorizonsResultsReader


class MyTestCase(unittest.TestCase):
    def test_lib_usage(self):
        """
        important parameter:
         'Azi_(a-app), Elev_(a-app),' =
          Airless apparent azimuth and elevation of target center. Compensated
        for light-time, the gravitational deflection of light, stellar aberration,
        precession and nutation. Azimuth is measured clockwise from north:

          North(0) -> East(90) -> South(180) -> West(270) -> North (360)

        Elevation angle is with respect to a plane perpendicular to the reference
        surface local zenith direction. TOPOCENTRIC ONLY.  Units: DEGREES
        """
        # 獲取 Altitude 和 Azimuth
        altitudes = 8.761056  # 高度 (度)
        azimuths = 302.897648  # 方位角 (度)
        # 繪製地平面和天體軌跡
        plt.figure(figsize=(8, 8))
        plt.subplot(projection="polar")
        # 繪製天體的軌跡
        plt.scatter(
            np.radians(azimuths), 90 - altitudes, label="Star Path", color="blue", s=1
        )  # s 是點的大小
        # 繪製地平面
        plt.fill_between(
            np.radians(np.linspace(0, 360, 100)), 0, 90, color="lightgrey", alpha=0.5
        )
        # 設置標題和標籤
        plt.title("Star Path on the Horizon", va="bottom")
        plt.xlabel("Azimuth (degrees)")
        plt.ylabel("Altitude (degrees)")
        # 設置極坐標的範圍
        plt.ylim(0, 90)
        # 加入圖例
        plt.legend()
        plt.grid(True)
        # 顯示圖形
        plt.show()
        # plt.savefig("test_plot.png")  # 保存圖形而不是顯示
        # plt.close()  # 關閉圖形
        # self.assertTrue(os.path.exists("test_plot.png"))
        # os.remove("test_plot.png")

    def test_draw_point(self):
        ret = HorizonsResultsReader("../assets/horizons_results.txt")
        data = ret.read()
        obs = SkyObserver(data)
        altitudes, azimuths = obs.observe()
        draw_polar(azimuths, altitudes, "test_plot.png")
        self.assertTrue(os.path.exists("test_plot.png"))
        os.remove("test_plot.png")


if __name__ == "__main__":
    unittest.main()
