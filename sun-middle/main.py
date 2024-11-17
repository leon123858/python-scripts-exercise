from services.sky_observer import SkyObserver, SkyObserverConfig, draw_polar
from utils.string_handle import HorizonsResultsReader


def main():
    # data from `https://ssd.jpl.nasa.gov/horizons/app.html#/`
    ret = HorizonsResultsReader("./assets/horizons_results5.txt")
    data = ret.read()
    config = SkyObserverConfig(lat=25.0478, lon=121.5319)
    obs = SkyObserver(data, config)
    altitudes, azimuths = obs.observe(start_index=0, num=1000)
    draw_polar(azimuths, altitudes)


if __name__ == "__main__":
    main()
