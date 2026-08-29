from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "ubpet"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=3)

try:
    from .secrets import (
        AREA_CODE as DEFAULT_AREA_CODE,
        APP_ID as DEFAULT_APP_ID,
        APP_KEY as DEFAULT_APP_KEY,
        BASE_URL as DEFAULT_BASE_URL,
        PRODUCT as DEFAULT_PRODUCT,
    )
except ImportError:
    DEFAULT_AREA_CODE = ""
    DEFAULT_APP_ID = ""
    DEFAULT_APP_KEY = ""
    DEFAULT_BASE_URL = ""
    DEFAULT_PRODUCT = ""

CONF_APP_KEY = "app_key"
CONF_APP_ID = "app_id"
CONF_AREA_CODE = "area_code"
CONF_COUNTRY = "country"
CONF_DEVICE_ID = "device_id"
CONF_BASE_URL = "base_url"
CONF_PRODUCT = "product"

EU_BASE_URL = "https://apis-eu.airrobo-home.com"
RUSSIA_BASE_URL = "https://apis-ru.airrobo-home.com"
JAPAN_BASE_URL = "https://apis-jp.airrobo-home.com"
# North America and Brazil sit on the ROOT apis host with NO regional dash
# prefix. Every other region follows the apis-XX pattern, so this is easy to
# get wrong - apis-us.airrobo-home.com does not resolve at all. Confirmed by
# the NA privacy policy served from
# https://apis.airrobo-home.com/na/v2/privacy.html
NA_BASE_URL = "https://apis.airrobo-home.com"

CONF_REGION = "region"

# The vendor ships THREE SEPARATE APPS and an account created in one will not
# authenticate against another's backend. The region must therefore be chosen
# by the user, not inferred from their country - somebody in Germany may well
# hold a UPET-NA account. Country is still sent as areaCode in the login body;
# it just no longer decides the host.
#
#   UPET        EU, UK, Turkey ............. data stored in Germany
#   UPET-NA     USA, North America, Brazil . data stored in USA
#   UPET-ASIA   Japan, South Korea ......... data stored in Japan
#   (Russia)    Russia
#
# Region names above come from the UPET privacy policy's data-residency table.
REGION_BASE_URLS = {
    "eu": EU_BASE_URL,
    "na": NA_BASE_URL,
    "asia": JAPAN_BASE_URL,
    "ru": RUSSIA_BASE_URL,
}
DEFAULT_REGION = "eu"

# Used only to preselect a sensible region in the config flow. The user can
# override it, which is the whole point - see the note above.
_REGION_HINTS = {
    "na": frozenset({"US", "CA", "MX", "BR", "PR", "CR", "PA", "GT", "DO"}),
    "asia": frozenset({"JP", "KR"}),
    "ru": frozenset({"RU"}),
}


def suggested_region_for_country(country: str) -> str:
    """Best-guess region for a country. Only a default; never authoritative."""
    for region, members in _REGION_HINTS.items():
        if country in members:
            return region
    return DEFAULT_REGION


def base_url_for_region(region: str) -> str:
    """Return the vendor API endpoint for a region key."""
    return REGION_BASE_URLS.get(region, EU_BASE_URL)

# Countries returned by the UPET 2.1.14 region map for the standard app.
SUPPORTED_COUNTRIES = (
    "AL",
    "AD",
    "AT",
    "BY",
    "BH",
    "BE",
    "BA",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FO",
    "FI",
    "FR",
    "GE",
    "DE",
    "GI",
    "GR",
    "HU",
    "IS",
    "IE",
    "IT",
    "KW",
    "XK",
    "LV",
    "LI",
    "LT",
    "LU",
    "MT",
    "MD",
    "MC",
    "ME",
    "NL",
    "MK",
    "NO",
    "PT",
    "PL",
    "QA",
    "RO",
    "RU",
    "SE",
    "CH",
    "SA",
    "SM",
    "RS",
    "SK",
    "SI",
    "ES",
    "TR",
    "UA",
    "GB",
    "AE",
    "VA",
    "US",
    "CA",
    "MX",
    "BR",
    "PR",
    "CR",
    "PA",
    "GT",
    "DO",
    "JP",
    "KR",
)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.TIME,
    Platform.SELECT,
    Platform.BUTTON,
]
