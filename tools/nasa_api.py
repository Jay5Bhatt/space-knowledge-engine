# tools/nasa_api.py

import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class NasaApi:
    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        # read key from environment (set via .env or system env)
        self.api_key = os.getenv("NASA_API_KEY")

    def fetch_apod(self) -> Dict:
        if self.demo_mode:
            return self._mock_apod()

        if not self.api_key:
            logger.warning("NASA_API_KEY not set. Falling back to mock APOD.")
            return self._mock_apod()

        try:
            import requests
        except Exception:
            logger.error("requests package not available, falling back to mock APOD.")
            return self._mock_apod()

        try:
            url = f"https://api.nasa.gov/planetary/apod?api_key={self.api_key}"
            resp = requests.get(url, timeout=8)
            data = resp.json()
            title = data.get("title", "NASA APOD")
            explanation = data.get("explanation", "")
            raw = f"{title}\n\n{explanation}"
            return {"id": "nasa_apod_live", "title": title, "source": "nasa_apod", "raw": raw}
        except Exception as e:
            logger.exception("Failed to fetch APOD: %s", e)
            return self._mock_apod()

    def fetch_mission(self, mission: str = "JWST") -> Dict:
        if self.demo_mode or not self.api_key:
            return self._mock_mission(mission)
        # Real mission API calls would go here; fallback to mock for safety
        return self._mock_mission(mission)

    def _mock_apod(self) -> Dict:
        return {
            "id": "nasa_apod_mock",
            "title": "Mock APOD: Pillars of Creation",
            "source": "nasa_apod_mock",
            "raw": (
                "Synthetic APOD entry. Description: The Pillars of Creation observed "
                "in infrared wavelengths reveal complex star-forming regions."
            ),
        }

    def _mock_mission(self, mission: str) -> Dict:
        return {
            "id": f"nasa_mission_{mission.lower()}_mock",
            "title": f"Mock NASA Mission: {mission}",
            "source": "nasa_mission_mock",
            "raw": (
                f"Synthetic mission update for {mission}. "
                "Instrumentation reports stable telemetry and recent spectroscopic measurements."
            ),
        }


if __name__ == "__main__":
    import logging as _log
    _log.basicConfig(level=_log.INFO)
    api = NasaApi(demo_mode=True)
    print(api.fetch_apod())
    print(api.fetch_mission("JWST"))
