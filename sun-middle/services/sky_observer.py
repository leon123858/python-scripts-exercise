import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class SkyObserverConfig:
    def __init__(self, lat=None, lon=None):
        self.lat = lat
        self.lon = lon


class SkyObserver:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def observe(self, start_index=0, num=1000):
        altitudes: list[float] = []
        azimuths: list[float] = []
        end_index = start_index + num
        for index, row in self.data.loc[start_index:end_index].iterrows():
            # 獲取 Altitude 和 Azimuth
            altitudes.append(float(row["Elev_(a-app)"]))  # 高度 (度)
            azimuths.append(float(row["Azi_(a-app)"]))  # 方位角 (度)
        return np.array(altitudes, dtype=float), np.array(azimuths, dtype=float)


def draw_polar(azimuths, altitudes, save_path=""):
    # 繪製地平面和天體軌跡
    plt.figure(figsize=(8, 8))
    plt.subplot(projection="polar")
    cmap = cm.viridis  # 你可以選擇其他顏色映射，如 cm.plasma, cm.inferno 等
    norm = plt.Normalize(0, len(azimuths) - 1)  # 正規化索引範圍
    # 為每個點分配顏色
    colors = [cmap(norm(i)) for i in range(len(azimuths))]
    # 繪製天體的軌跡
    plt.scatter(
        np.radians(azimuths), 90 - altitudes, label="Star Path", color=colors, s=10
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

    if save_path != "":
        plt.savefig(save_path)
    else:
        plt.show()
