from __future__ import annotations

import json
import math
from pathlib import Path
import re
import threading
import time
from typing import Any

import httpx

from core.region_manager import RegionGraphManager
from core.route_engine import RouteEngine

BASE_DIR = (
    Path(__file__).resolve().parent.parent
    if Path(__file__).resolve().parent.name in ("core", "services", "scripts", "tests")
    else Path(__file__).resolve().parent
)
CACHE_DIR = BASE_DIR / "data" / "cache"
GEOCODE_CACHE_PATH = CACHE_DIR / "geocode_cache.json"

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = (
    "NERSmartRoute-CSE276-SIH26002/1.0 (Academic Logistics Research Project; local-dev)"
)
OSM_ATTRIBUTION = "Place data © OpenStreetMap contributors (ODbL)"
MIN_NOMINATIM_INTERVAL_S = 1.10

# Verified Gazetteer of Meghalaya, North-East India, and National Reference Locations
# Categorized accurately with WGS84 coordinates and elevation (m)
LOCAL_GAZETTEER: list[dict[str, Any]] = [
    # --- Routable inside Phase 1 Shillong-Sohra Graph (within 3,000 m snap limit) ---
    {
        "place_id": "shillong",
        "name": "Shillong (HQ Logistics Hub)",
        "display_name": "Shillong (HQ Logistics Hub), East Khasi Hills, Meghalaya, India",
        "aliases": ["shillong", "shillong meghalaya", "east khasi hills", "shillong hq"],
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.5788,
        "lng": 91.8933,
        "elevation_m": 1496,
        "place_type": "hub",
        "description": "Central NER disaster logistics coordination center & civil hospital staging depot",
    },
    {
        "place_id": "police_bazar_shillong",
        "name": "Police Bazar, Shillong",
        "display_name": "Police Bazar (Khyndailad), Shillong, East Khasi Hills, Meghalaya, India",
        "aliases": ["police bazar", "khyndailad", "police bazaar shillong"],
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.5769,
        "lng": 91.8831,
        "elevation_m": 1490,
        "place_type": "urban_center",
        "description": "Commercial core and central urban transit node of Shillong",
    },
    {
        "place_id": "laitumkhrah_shillong",
        "name": "Laitumkhrah, Shillong",
        "display_name": "Laitumkhrah, Shillong, East Khasi Hills, Meghalaya, India",
        "aliases": ["laitumkhrah", "laitumkhrah shillong"],
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.5712,
        "lng": 91.8995,
        "elevation_m": 1515,
        "place_type": "urban_ward",
        "description": "Eastern Shillong hospital, institutional, and municipal distribution zone",
    },
    {
        "place_id": "upper_shillong",
        "name": "Upper Shillong (7th Mile Staging Hub)",
        "display_name": "Upper Shillong, East Khasi Hills, Meghalaya, India",
        "aliases": ["upper shillong", "7th mile shillong", "shillong peak road"],
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.5415,
        "lng": 91.8490,
        "elevation_m": 1820,
        "place_type": "hub",
        "description": "High-altitude western junction splitting corridors toward Sohra and Mairang",
    },
    {
        "place_id": "smit_meghalaya",
        "name": "Smit (Eastern Plateau Supply Point)",
        "display_name": "Smit, East Khasi Hills, Meghalaya, India",
        "aliases": ["smit", "smit meghalaya", "smit shillong"],
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.5186,
        "lng": 91.9462,
        "elevation_m": 1610,
        "place_type": "outpost",
        "description": "Rural plateau agricultural and relief distribution town",
    },
    {
        "place_id": "mawphlang",
        "name": "Mawphlang (Central Highland Junction)",
        "display_name": "Mawphlang, East Khasi Hills, Meghalaya, India",
        "aliases": ["mawphlang", "mawphlang meghalaya"],
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.4518,
        "lng": 91.7568,
        "elevation_m": 1780,
        "place_type": "outpost",
        "description": "Mid-plateau highland transit town along the western ridge corridor",
    },
    {
        "place_id": "sohra",
        "name": "Sohra / Cherrapunji (Southern Hills)",
        "display_name": "Sohra (Cherrapunji), East Khasi Hills, Meghalaya, India",
        "aliases": ["sohra", "cherrapunji", "cherrapunjee", "sohra meghalaya"],
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.2750,
        "lng": 91.7323,
        "elevation_m": 1430,
        "place_type": "destination",
        "description": "High-precipitation monsoon escarpment corridor with steep canyon access routes",
    },
    {
        "place_id": "mairang",
        "name": "Mairang (West Khasi Hills Transit)",
        "display_name": "Mairang, Eastern West Khasi Hills, Meghalaya, India",
        "aliases": ["mairang", "mairang meghalaya", "west khasi hills"],
        "state": "Meghalaya",
        "district": "Eastern West Khasi Hills",
        "lat": 25.5653,
        "lng": 91.6375,
        "elevation_m": 1620,
        "place_type": "outpost",
        "description": "Highland plateau transit point on NH-106 with vulnerable ridge cuts",
    },
    {
        "place_id": "pynursla",
        "name": "Pynursla (Southern Ridge Outpost)",
        "display_name": "Pynursla, East Khasi Hills, Meghalaya, India",
        "aliases": ["pynursla", "pynursla meghalaya"],
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.3112,
        "lng": 91.8942,
        "elevation_m": 1390,
        "place_type": "outpost",
        "description": "Southern ridge town on NH-206 en route to Dawki border terminal",
    },
    {
        "place_id": "dawki",
        "name": "Dawki (Border River Outpost)",
        "display_name": "Dawki (Tamabil Border), West Jaintia Hills, Meghalaya, India",
        "aliases": ["dawki", "dawki meghalaya", "tamabil", "umngot"],
        "state": "Meghalaya",
        "district": "West Jaintia Hills",
        "lat": 25.1911,
        "lng": 92.0232,
        "elevation_m": 85,
        "place_type": "outpost",
        "description": "Umngot river crossing border outpost and low-altitude supply terminal",
    },
    # --- Phase 2 / Phase 3 Expandable Regional Corridors ---
    {
        "place_id": "jowai",
        "name": "Jowai (Jaintia Hills Sub-Depot)",
        "display_name": "Jowai, West Jaintia Hills, Meghalaya, India",
        "aliases": ["jowai", "jowai meghalaya", "jaintia hills"],
        "state": "Meghalaya",
        "district": "West Jaintia Hills",
        "lat": 25.4475,
        "lng": 92.2030,
        "elevation_m": 1380,
        "place_type": "depot",
        "description": "Eastern Meghalaya supply junction on NH-6 (requires Jaintia Hills regional graph)",
    },
    {
        "place_id": "nongpoh",
        "name": "Nongpoh (NH-6 Transit Hub)",
        "display_name": "Nongpoh, Ri-Bhoi District, Meghalaya, India",
        "aliases": ["nongpoh", "nongpoh meghalaya", "ri bhoi", "ri-bhoi"],
        "state": "Meghalaya",
        "district": "Ri-Bhoi",
        "lat": 25.9037,
        "lng": 91.8803,
        "elevation_m": 485,
        "place_type": "outpost",
        "description": "Midway transit corridor connecting Guwahati plain with Shillong plateau on NH-6",
    },
    {
        "place_id": "byrnihat",
        "name": "Byrnihat (Assam–Meghalaya Border Logistics Park)",
        "display_name": "Byrnihat, Ri-Bhoi District, Meghalaya, India",
        "aliases": ["byrnihat", "burnihat", "byrnihat meghalaya"],
        "state": "Meghalaya",
        "district": "Ri-Bhoi",
        "lat": 26.0462,
        "lng": 91.8705,
        "elevation_m": 140,
        "place_type": "depot",
        "description": "Industrial warehousing and border freight checkpoint on NH-6",
    },
    {
        "place_id": "guwahati",
        "name": "Guwahati (Regional Depot)",
        "display_name": "Guwahati, Kamrup Metropolitan, Assam, India",
        "aliases": ["guwahati", "guwahati assam", "gauhati", "dispur"],
        "state": "Assam",
        "district": "Kamrup Metropolitan",
        "lat": 26.1445,
        "lng": 91.7362,
        "elevation_m": 55,
        "place_type": "depot",
        "description": "Brahmaputra valley multimodal rail & highway logistics terminal",
    },
    # --- Broader North-East & India Reference Cities (Out of Current Graph Coverage) ---
    {
        "place_id": "tura_meghalaya",
        "name": "Tura (Garo Hills Regional Hub)",
        "display_name": "Tura, West Garo Hills, Meghalaya, India",
        "aliases": ["tura", "tura meghalaya", "garo hills"],
        "state": "Meghalaya",
        "district": "West Garo Hills",
        "lat": 25.5142,
        "lng": 90.2036,
        "elevation_m": 349,
        "place_type": "hub",
        "description": "Western Meghalaya administrative and disaster relief center",
    },
    {
        "place_id": "silchar_assam",
        "name": "Silchar (Barak Valley Logistics Hub)",
        "display_name": "Silchar, Cachar, Assam, India",
        "aliases": ["silchar", "silchar assam", "barak valley"],
        "state": "Assam",
        "district": "Cachar",
        "lat": 24.8333,
        "lng": 92.7789,
        "elevation_m": 25,
        "place_type": "depot",
        "description": "Southern Assam railhead serving Mizoram, Tripura, and southern Meghalaya",
    },
    {
        "place_id": "tezpur_assam",
        "name": "Tezpur (Northern Brahmaputra Staging Base)",
        "display_name": "Tezpur, Sonitpur, Assam, India",
        "aliases": ["tezpur", "tezpur assam"],
        "state": "Assam",
        "district": "Sonitpur",
        "lat": 26.6528,
        "lng": 92.7926,
        "elevation_m": 73,
        "place_type": "depot",
        "description": "Forward logistics staging base for Arunachal Pradesh corridors",
    },
    {
        "place_id": "imphal_manipur",
        "name": "Imphal, Manipur",
        "display_name": "Imphal, Imphal West, Manipur, India",
        "aliases": ["imphal", "imphal manipur"],
        "state": "Manipur",
        "district": "Imphal West",
        "lat": 24.8170,
        "lng": 93.9368,
        "elevation_m": 786,
        "place_type": "capital",
        "description": "State capital of Manipur",
    },
    {
        "place_id": "aizawl_mizoram",
        "name": "Aizawl, Mizoram",
        "display_name": "Aizawl, Mizoram, India",
        "aliases": ["aizawl", "aizawl mizoram"],
        "state": "Mizoram",
        "district": "Aizawl",
        "lat": 23.7271,
        "lng": 92.7176,
        "elevation_m": 1132,
        "place_type": "capital",
        "description": "State capital of Mizoram",
    },
    {
        "place_id": "kohima_nagaland",
        "name": "Kohima, Nagaland",
        "display_name": "Kohima, Nagaland, India",
        "aliases": ["kohima", "kohima nagaland"],
        "state": "Nagaland",
        "district": "Kohima",
        "lat": 25.6751,
        "lng": 94.1086,
        "elevation_m": 1444,
        "place_type": "capital",
        "description": "State capital of Nagaland",
    },
    {
        "place_id": "itanagar_arunachal",
        "name": "Itanagar, Arunachal Pradesh",
        "display_name": "Itanagar, Papum Pare, Arunachal Pradesh, India",
        "aliases": ["itanagar", "itanagar arunachal"],
        "state": "Arunachal Pradesh",
        "district": "Papum Pare",
        "lat": 27.0844,
        "lng": 93.6053,
        "elevation_m": 320,
        "place_type": "capital",
        "description": "State capital of Arunachal Pradesh",
    },
    {
        "place_id": "agartala_tripura",
        "name": "Agartala, Tripura",
        "display_name": "Agartala, West Tripura, Tripura, India",
        "aliases": ["agartala", "agartala tripura"],
        "state": "Tripura",
        "district": "West Tripura",
        "lat": 23.8315,
        "lng": 91.2868,
        "elevation_m": 13,
        "place_type": "capital",
        "description": "State capital of Tripura and ICP border trade terminal on NH-8",
    },
    {
        "place_id": "gangtok_sikkim",
        "name": "Gangtok, Sikkim",
        "display_name": "Gangtok, East Sikkim, Sikkim, India",
        "aliases": ["gangtok", "gangtok sikkim", "sikkim"],
        "state": "Sikkim",
        "district": "East Sikkim",
        "lat": 27.3389,
        "lng": 88.6065,
        "elevation_m": 1650,
        "place_type": "capital",
        "description": "State capital of Sikkim and primary Himalayan logistics hub on NH-10",
    },
    {
        "place_id": "rangpo_sikkim",
        "name": "Rangpo (Sikkim Border Gateway)",
        "display_name": "Rangpo, Pakyong District, Sikkim, India",
        "aliases": ["rangpo", "rangpo sikkim"],
        "state": "Sikkim",
        "district": "Pakyong",
        "lat": 27.1774,
        "lng": 88.5336,
        "elevation_m": 330,
        "place_type": "depot",
        "description": "Teesta valley checkpost and pharmaceutical/freight staging gateway into Sikkim on NH-10",
    },
    {
        "place_id": "dimapur_nagaland",
        "name": "Dimapur (Nagaland Rail & Air Logistics Hub)",
        "display_name": "Dimapur, Dimapur District, Nagaland, India",
        "aliases": ["dimapur", "dimapur nagaland"],
        "state": "Nagaland",
        "district": "Dimapur",
        "lat": 25.9091,
        "lng": 93.7266,
        "elevation_m": 145,
        "place_type": "depot",
        "description": "Primary railhead, airport, and commercial freight entry terminal for Nagaland and Manipur on NH-29",
    },
    {
        "place_id": "naharlagun_arunachal",
        "name": "Naharlagun (Capital Railhead), Arunachal Pradesh",
        "display_name": "Naharlagun, Papum Pare, Arunachal Pradesh, India",
        "aliases": ["naharlagun", "naharlagun arunachal"],
        "state": "Arunachal Pradesh",
        "district": "Papum Pare",
        "lat": 27.1045,
        "lng": 93.6952,
        "elevation_m": 200,
        "place_type": "depot",
        "description": "Primary rail terminal and warehousing hub serving the Itanagar Capital Complex on NH-415",
    },
    {
        "place_id": "thoubal_manipur",
        "name": "Thoubal, Manipur",
        "display_name": "Thoubal, Thoubal District, Manipur, India",
        "aliases": ["thoubal", "thoubal manipur"],
        "state": "Manipur",
        "district": "Thoubal",
        "lat": 24.6340,
        "lng": 94.0006,
        "elevation_m": 790,
        "place_type": "outpost",
        "description": "Southeastern Imphal valley agricultural and transit hub on NH-102",
    },
    {
        "place_id": "lunglei_mizoram",
        "name": "Lunglei (Southern Mizoram Hub)",
        "display_name": "Lunglei, Lunglei District, Mizoram, India",
        "aliases": ["lunglei", "lunglei mizoram"],
        "state": "Mizoram",
        "district": "Lunglei",
        "lat": 22.8880,
        "lng": 92.7343,
        "elevation_m": 1222,
        "place_type": "hub",
        "description": "Secondary administrative and relief distribution center of southern Mizoram on NH-54",
    },
    {
        "place_id": "udaipur_tripura",
        "name": "Udaipur, Tripura",
        "display_name": "Udaipur, Gomati District, Tripura, India",
        "aliases": ["udaipur tripura", "gomati tripura"],
        "state": "Tripura",
        "district": "Gomati",
        "lat": 23.5333,
        "lng": 91.4833,
        "elevation_m": 22,
        "place_type": "outpost",
        "description": "Southern Tripura highway junction on NH-8",
    },
    {
        "place_id": "new_delhi",
        "name": "New Delhi, Delhi",
        "display_name": "New Delhi, National Capital Territory of Delhi, India",
        "aliases": ["new delhi", "delhi", "delhi india"],
        "state": "Delhi",
        "district": "New Delhi",
        "lat": 28.6139,
        "lng": 77.2090,
        "elevation_m": 216,
        "place_type": "hub",
        "description": "National capital multimodal highway and freight logistics hub",
    },
    {
        "place_id": "hoshiarpur_punjab",
        "name": "Hoshiarpur, Punjab",
        "display_name": "Hoshiarpur, Punjab, India",
        "aliases": ["hoshiarpur", "hoshiarpur punjab"],
        "state": "Punjab",
        "district": "Hoshiarpur",
        "lat": 31.5322,
        "lng": 75.9115,
        "elevation_m": 296,
        "place_type": "hub",
        "description": "Sub-Shivalik Doaba logistics and agricultural transit center in Punjab",
    },
    {
        "place_id": "jalandhar_punjab",
        "name": "Jalandhar, Punjab",
        "display_name": "Jalandhar, Punjab, India",
        "aliases": ["jalandhar", "jalandhar punjab", "jullundur"],
        "state": "Punjab",
        "district": "Jalandhar",
        "lat": 31.3260,
        "lng": 75.5762,
        "elevation_m": 228,
        "place_type": "hub",
        "description": "Major Grand Trunk Road (NH-44) industrial and highway junction in Punjab",
    },
    {
        "place_id": "ludhiana_punjab",
        "name": "Ludhiana, Punjab",
        "display_name": "Ludhiana, Punjab, India",
        "aliases": ["ludhiana", "ludhiana punjab"],
        "state": "Punjab",
        "district": "Ludhiana",
        "lat": 30.9010,
        "lng": 75.8573,
        "elevation_m": 244,
        "place_type": "depot",
        "description": "Primary industrial and freight distribution hub of Punjab on NH-44",
    },
    {
        "place_id": "amritsar_punjab",
        "name": "Amritsar, Punjab",
        "display_name": "Amritsar, Punjab, India",
        "aliases": ["amritsar", "amritsar punjab"],
        "state": "Punjab",
        "district": "Amritsar",
        "lat": 31.6340,
        "lng": 74.8723,
        "elevation_m": 234,
        "place_type": "hub",
        "description": "Northwestern border trade and logistics terminal in Majha, Punjab",
    },
    {
        "place_id": "chandigarh",
        "name": "Chandigarh",
        "display_name": "Chandigarh, Union Territory, India",
        "aliases": ["chandigarh", "chandigarh india", "tricity"],
        "state": "Chandigarh",
        "district": "Chandigarh",
        "lat": 30.7333,
        "lng": 76.7794,
        "elevation_m": 321,
        "place_type": "hub",
        "description": "Northern regional capital and Himalayan foothills gateway hub",
    },
    {
        "place_id": "mumbai_maharashtra",
        "name": "Mumbai, Maharashtra",
        "display_name": "Mumbai, Maharashtra, India",
        "aliases": ["mumbai", "bombay", "mumbai maharashtra"],
        "state": "Maharashtra",
        "district": "Mumbai",
        "lat": 19.0760,
        "lng": 72.8777,
        "elevation_m": 14,
        "place_type": "depot",
        "description": "Western India maritime port and national expressway freight terminal",
    },
    {
        "place_id": "bengaluru_karnataka",
        "name": "Bengaluru, Karnataka",
        "display_name": "Bengaluru (Bangalore), Karnataka, India",
        "aliases": ["bengaluru", "bangalore", "bengaluru karnataka"],
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "lat": 12.9716,
        "lng": 77.5946,
        "elevation_m": 920,
        "place_type": "hub",
        "description": "Southern plateau multimodal highway and industrial logistics center",
    },
    {
        "place_id": "chennai_tamil_nadu",
        "name": "Chennai, Tamil Nadu",
        "display_name": "Chennai (Madras), Tamil Nadu, India",
        "aliases": ["chennai", "madras", "chennai tamil nadu"],
        "state": "Tamil Nadu",
        "district": "Chennai",
        "lat": 13.0827,
        "lng": 80.2707,
        "elevation_m": 7,
        "place_type": "depot",
        "description": "Southeastern coastal port and Golden Quadrilateral highway terminal",
    },
    {
        "place_id": "hyderabad_telangana",
        "name": "Hyderabad, Telangana",
        "display_name": "Hyderabad, Telangana, India",
        "aliases": ["hyderabad", "hyderabad telangana"],
        "state": "Telangana",
        "district": "Hyderabad",
        "lat": 17.3850,
        "lng": 78.4867,
        "elevation_m": 542,
        "place_type": "hub",
        "description": "Central Deccan North–South corridor logistics hub on NH-44",
    },
    {
        "place_id": "kolkata_west_bengal",
        "name": "Kolkata, West Bengal",
        "display_name": "Kolkata (Calcutta), West Bengal, India",
        "aliases": ["kolkata", "calcutta", "kolkata west bengal"],
        "state": "West Bengal",
        "district": "Kolkata",
        "lat": 22.5726,
        "lng": 88.3639,
        "elevation_m": 9,
        "place_type": "depot",
        "description": "Eastern India port and primary freight gateway to North-East India",
    },
    {
        "place_id": "jaipur_rajasthan",
        "name": "Jaipur, Rajasthan",
        "display_name": "Jaipur, Rajasthan, India",
        "aliases": ["jaipur", "jaipur rajasthan"],
        "state": "Rajasthan",
        "district": "Jaipur",
        "lat": 26.9124,
        "lng": 75.7873,
        "elevation_m": 431,
        "place_type": "hub",
        "description": "Western freight corridor junction on NH-48",
    },
    {
        "place_id": "lucknow_up",
        "name": "Lucknow, Uttar Pradesh",
        "display_name": "Lucknow, Uttar Pradesh, India",
        "aliases": ["lucknow", "lucknow uttar pradesh", "lucknow up"],
        "state": "Uttar Pradesh",
        "district": "Lucknow",
        "lat": 26.8467,
        "lng": 80.9462,
        "elevation_m": 123,
        "place_type": "hub",
        "description": "Gangetic plain expressway and central northern distribution hub",
    },
    {
        "place_id": "ahmedabad_gujarat",
        "name": "Ahmedabad, Gujarat",
        "display_name": "Ahmedabad, Gujarat, India",
        "aliases": ["ahmedabad", "ahmedabad gujarat"],
        "state": "Gujarat",
        "district": "Ahmedabad",
        "lat": 23.0225,
        "lng": 72.5714,
        "elevation_m": 53,
        "place_type": "depot",
        "description": "Western industrial and expressway logistics hub",
    },
]

_COORD_REGEX = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*(?:,\s*|\s+)\s*([+-]?\d+(?:\.\d+)?)\s*$"
)


class GeocodingError(Exception):
    """Base exception for geocoding errors."""


class EmptyGeocodeQueryError(GeocodingError, ValueError):
    """Raised when a search query is empty or whitespace-only."""


class InvalidCoordinateQueryError(GeocodingError, ValueError):
    """Raised when a user enters a numeric coordinate pair outside valid WGS84 bounds."""


def _normalize_query(q: str) -> str:
    cleaned = re.sub(r"[,;/()]+", " ", q.strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class GeocodingService:
    """
    Two-tier geocoding service with:
      1. Instant offline local gazetteer + coordinate parser.
      2. Rate-limited, disk-cached OpenStreetMap Nominatim lookup with graceful offline fallback.
      3. Separate road-graph coverage validation via RegionGraphManager.
    """

    _rate_lock = threading.Lock()
    _last_external_call_ts: float = 0.0

    def __init__(
        self,
        region_manager: RegionGraphManager | None = None,
        cache_path: str | Path = GEOCODE_CACHE_PATH,
        allow_external_nominatim: bool = True,
    ) -> None:
        self.region_manager = region_manager or RegionGraphManager()
        self.cache_path = Path(cache_path).resolve()
        self.allow_external_nominatim = bool(allow_external_nominatim)
        self._cache: dict[str, list[dict[str, Any]]] = self._load_disk_cache()

    def _load_disk_cache(self) -> dict[str, list[dict[str, Any]]]:
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_disk_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _try_parse_coordinate_query(raw_query: str) -> dict[str, Any] | None:
        match = _COORD_REGEX.match(raw_query)
        if not match:
            return None
        lat = float(match.group(1))
        lng = float(match.group(2))
        if not (math.isfinite(lat) and math.isfinite(lng)):
            raise InvalidCoordinateQueryError("Coordinates must be finite numbers.")
        if lat < -90.0 or lat > 90.0:
            raise InvalidCoordinateQueryError(
                f"Latitude {lat} is outside valid bounds [-90.0, 90.0]."
            )
        if lng < -180.0 or lng > 180.0:
            raise InvalidCoordinateQueryError(
                f"Longitude {lng} is outside valid bounds [-180.0, 180.0]."
            )
        return {
            "place_id": f"coord_{lat:.5f}_{lng:.5f}",
            "name": f"Coordinate ({lat:.4f}°N, {lng:.4f}°E)",
            "display_name": f"Direct WGS84 Coordinate ({lat:.5f}, {lng:.5f})",
            "state": "Custom Coordinate",
            "district": "",
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "elevation_m": 1000,
            "place_type": "coordinate",
            "source": "direct_coordinate_input",
            "description": "User-specified geographic coordinate pair.",
        }

    @staticmethod
    def _search_local_gazetteer(norm_q: str, limit: int = 6) -> list[dict[str, Any]]:
        if not norm_q:
            return []

        tokens = [
            tok
            for tok in re.split(r"[\s,/()-]+", norm_q)
            if tok and tok not in ("india", "ner")
        ]
        scored: list[tuple[float, dict[str, Any]]] = []

        for entry in LOCAL_GAZETTEER:
            name_low = entry["name"].lower()
            disp_low = entry["display_name"].lower()
            state_low = entry["state"].lower()
            pid_low = entry["place_id"].lower()
            aliases = [a.lower() for a in entry.get("aliases", [])]

            score = 0.0
            if norm_q == pid_low or norm_q in aliases or norm_q == name_low:
                score = 100.0
            elif any(a.startswith(norm_q) for a in aliases) or name_low.startswith(norm_q):
                score = 88.0
            elif norm_q in name_low or any(norm_q in a for a in aliases):
                score = 78.0
            elif norm_q in disp_low:
                score = 68.0
            elif tokens:
                matched_tokens = sum(
                    1
                    for t in tokens
                    if (
                        t in name_low
                        or t in disp_low
                        or t in state_low
                        or any(t in a for a in aliases)
                    )
                )
                if matched_tokens == len(tokens):
                    score = 62.0
                elif matched_tokens > 0 and len(tokens) > 1:
                    score = 35.0 * (matched_tokens / len(tokens))

            if score > 0:
                scored.append(
                    (
                        score,
                        {
                            "place_id": entry["place_id"],
                            "name": entry["name"],
                            "display_name": entry["display_name"],
                            "state": entry["state"],
                            "district": entry.get("district", ""),
                            "lat": float(entry["lat"]),
                            "lng": float(entry["lng"]),
                            "elevation_m": int(entry.get("elevation_m", 1000)),
                            "place_type": entry.get("place_type", "place"),
                            "source": "verified_local_gazetteer",
                            "description": entry.get("description", ""),
                        },
                    )
                )

        scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
        return [item for _, item in scored[:limit]]

    def _query_nominatim_cached(
        self, norm_q: str, limit: int = 5
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Query OpenStreetMap Nominatim with persistent disk caching and 1.1s rate limiting.
        Returns (results, source_status).
        """
        if norm_q in self._cache:
            return self._cache[norm_q][:limit], "nominatim_disk_cache"

        if not self.allow_external_nominatim:
            return [], "offline_local_only"

        with GeocodingService._rate_lock:
            elapsed = time.monotonic() - GeocodingService._last_external_call_ts
            if elapsed < MIN_NOMINATIM_INTERVAL_S:
                time.sleep(MIN_NOMINATIM_INTERVAL_S - elapsed)
            GeocodingService._last_external_call_ts = time.monotonic()

        try:
            with httpx.Client(
                timeout=3.5,
                headers={"User-Agent": NOMINATIM_USER_AGENT, "Accept-Language": "en"},
            ) as client:
                resp = client.get(
                    NOMINATIM_SEARCH_URL,
                    params={
                        "q": norm_q,
                        "format": "jsonv2",
                        "addressdetails": 1,
                        "countrycodes": "in",
                        "limit": max(1, min(10, limit)),
                    },
                )
                if resp.status_code != 200:
                    return [], f"nominatim_http_{resp.status_code}"
                raw_items = resp.json()
        except Exception:
            return [], "offline_fallback"

        parsed: list[dict[str, Any]] = []
        if isinstance(raw_items, list):
            for idx, item in enumerate(raw_items):
                try:
                    lat = round(float(item["lat"]), 6)
                    lng = round(float(item["lon"]), 6)
                except (KeyError, TypeError, ValueError):
                    continue
                addr = item.get("address") or {}
                state = str(addr.get("state") or addr.get("region") or "India")
                district = str(
                    addr.get("state_district") or addr.get("county") or addr.get("city") or ""
                )
                short_name = str(
                    item.get("name")
                    or addr.get("city")
                    or addr.get("town")
                    or addr.get("village")
                    or item.get("display_name", "").split(",")[0]
                )
                parsed.append(
                    {
                        "place_id": f"osm_{item.get('osm_id', idx)}",
                        "name": f"{short_name}, {state}" if state and state not in short_name else short_name,
                        "display_name": str(item.get("display_name", short_name)),
                        "state": state,
                        "district": district,
                        "lat": lat,
                        "lng": lng,
                        "elevation_m": 1000,
                        "place_type": str(item.get("type") or item.get("category") or "place"),
                        "source": "openstreetmap_nominatim",
                        "description": f"OpenStreetMap {item.get('type', 'location')} in {state}",
                    }
                )

        if parsed:
            self._cache[norm_q] = parsed
            self._save_disk_cache()

        return parsed[:limit], "openstreetmap_nominatim"

    def search_places(
        self,
        query: str,
        limit: int = 6,
        active_engine: RouteEngine | None = None,
    ) -> dict[str, Any]:
        """
        Search for origin/destination places by text or coordinate string and attach
        road-network coverage metadata to every candidate result.
        """
        if not isinstance(query, str) or not query.strip():
            raise EmptyGeocodeQueryError(
                "Location search query cannot be empty. Enter a place name (e.g., 'Shillong, Meghalaya') or coordinates ('25.5788, 91.8933')."
            )

        raw_q = query.strip()
        norm_q = _normalize_query(raw_q)
        max_results = max(1, min(12, int(limit)))

        # 1. Check direct coordinate pair first
        coord_item = self._try_parse_coordinate_query(raw_q)
        if coord_item is not None:
            cov = self.region_manager.evaluate_point_coverage(
                coord_item["lat"], coord_item["lng"], active_engine=active_engine
            )
            return {
                "query": raw_q,
                "geocoder_source": "direct_coordinate_parser",
                "attribution": OSM_ATTRIBUTION,
                "count": 1,
                "results": [{**coord_item, "coverage": cov}],
            }

        # 2. Search Tier-1 verified local gazetteer
        local_matches = self._search_local_gazetteer(norm_q, limit=max_results)
        geocoder_source = "verified_local_gazetteer"
        combined = list(local_matches)

        # 3. If fewer than 2 local matches and external Nominatim is enabled, query cached Nominatim
        if len(combined) < 2 and self.allow_external_nominatim:
            ext_matches, ext_status = self._query_nominatim_cached(norm_q, limit=max_results)
            if ext_matches:
                geocoder_source = (
                    f"verified_local_gazetteer+{ext_status}" if combined else ext_status
                )
                for ext in ext_matches:
                    is_dup = any(
                        math.hypot(ext["lat"] - c["lat"], ext["lng"] - c["lng"]) < 0.01
                        for c in combined
                    )
                    if not is_dup and len(combined) < max_results:
                        combined.append(ext)
            elif not combined:
                geocoder_source = ext_status

        # 4. Attach road-graph coverage metadata to every candidate
        enriched_results: list[dict[str, Any]] = []
        for item in combined[:max_results]:
            cov = self.region_manager.evaluate_point_coverage(
                item["lat"], item["lng"], active_engine=active_engine
            )
            enriched_results.append({**item, "coverage": cov})

        return {
            "query": raw_q,
            "geocoder_source": geocoder_source,
            "attribution": OSM_ATTRIBUTION,
            "count": len(enriched_results),
            "results": enriched_results,
        }

    def list_default_suggestions(
        self, active_engine: RouteEngine | None = None
    ) -> list[dict[str, Any]]:
        """Return the primary NER logistics hubs with live coverage status for quick selection."""
        featured_ids = [
            "shillong",
            "sohra",
            "mairang",
            "dawki",
            "pynursla",
            "mawphlang",
            "smit_meghalaya",
            "upper_shillong",
            "guwahati",
            "jowai",
            "nongpoh",
            "itanagar_arunachal",
            "imphal_manipur",
            "aizawl_mizoram",
            "kohima_nagaland",
            "agartala_tripura",
            "gangtok_sikkim",
        ]
        results: list[dict[str, Any]] = []
        for pid in featured_ids:
            entry = next((e for e in LOCAL_GAZETTEER if e["place_id"] == pid), None)
            if entry is None:
                continue
            cov = self.region_manager.evaluate_point_coverage(
                float(entry["lat"]), float(entry["lng"]), active_engine=active_engine
            )
            results.append(
                {
                    "place_id": entry["place_id"],
                    "name": entry["name"],
                    "display_name": entry["display_name"],
                    "state": entry["state"],
                    "district": entry.get("district", ""),
                    "lat": float(entry["lat"]),
                    "lng": float(entry["lng"]),
                    "elevation_m": int(entry.get("elevation_m", 1000)),
                    "place_type": entry.get("place_type", "hub"),
                    "source": "verified_local_gazetteer",
                    "description": entry.get("description", ""),
                    "coverage": cov,
                }
            )
        return results
