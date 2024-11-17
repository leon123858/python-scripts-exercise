from services.sky_observer import SkyObserver, draw_polar
from utils.string_handle import HorizonsResultsReader


def main():
    # data from `https://ssd.jpl.nasa.gov/horizons/app.html#/`
    ret = HorizonsResultsReader("./assets/horizons_results9.txt")
    data = ret.read()
    obs = SkyObserver(data)
    altitudes, azimuths = obs.observe(start_index=0, num=2000)
    draw_polar(azimuths, altitudes)
    # note: 逆行現象是跟星座的相對位置做比較!


if __name__ == "__main__":
    main()
