import os
import unittest

import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time

from services.sky_observer import SkyObserver, SkyObserverConfig, draw_polar
from utils.string_handle import HorizonsResultsReader


class MyTestCase(unittest.TestCase):
    def test_lib_usage(self):
        # 設定觀測地點，這裡以台北為例
        location = EarthLocation(
            lat=25.0478 * u.deg, lon=121.5319 * u.deg, height=0 * u.m
        )
        # 設定觀測時間
        times = Time("2023-10-01 00:00:00") + np.linspace(0, 1, 100) * u.day  # 觀測一天
        # 真實數據 R.A 和 Dec
        ra_str = "08 34 28.17"
        dec_str = "+21 20 40.5"
        # 將字串轉換為 SkyCoord 物件
        star_coord = SkyCoord(
            ra=ra_str, dec=dec_str, unit=(u.hourangle, u.deg), frame="icrs"
        )
        # 計算星星在不同時間的 Alt/Az
        altaz_frame = AltAz(obstime=times, location=location)
        star_altaz = star_coord.transform_to(altaz_frame)
        # 獲取 Altitude 和 Azimuth
        altitudes = star_altaz.alt.deg  # 高度 (度)
        azimuths = star_altaz.az.deg  # 方位角 (度)
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
        plt.savefig("test_plot.png")  # 保存圖形而不是顯示
        plt.close()  # 關閉圖形
        self.assertTrue(os.path.exists("test_plot.png"))
        os.remove("test_plot.png")

    def test_draw_point(self):
        ret = HorizonsResultsReader("./assets/horizons_results.txt")
        data = ret.read()
        config = SkyObserverConfig(lat=25.0478, lon=121.5319)
        self.assertEqual(config.lat, 25.0478)
        self.assertEqual(config.lon, 121.5319)
        obs = SkyObserver(data, config)
        altitudes, azimuths = obs.observe()
        draw_polar(azimuths, altitudes, "test_plot.png")
        self.assertTrue(os.path.exists("test_plot.png"))
        os.remove("test_plot.png")


if __name__ == "__main__":
    unittest.main()
