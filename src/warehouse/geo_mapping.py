"""Country -> (continent, region) mapping for dim_location population.

Regions follow loose UN sub-region buckets. Used to populate dim_continent /
dim_region / dim_location. Unknown countries fall back to ("Other", "Other")
so the load doesn't fail on a new country code.
"""
from __future__ import annotations

# (continent_name, region_name)
COUNTRY_TO_REGION: dict[str, tuple[str, str]] = {
    # ===== North America =====
    "United States": ("North America", "Northern America"),
    "Canada": ("North America", "Northern America"),
    "Mexico": ("North America", "Central America"),
    "Costa Rica": ("North America", "Central America"),
    "Honduras": ("North America", "Central America"),
    "Dominican Republic": ("North America", "Caribbean"),
    "Puerto Rico": ("North America", "Caribbean"),
    "Bahamas": ("North America", "Caribbean"),
    # ===== South America =====
    "Brazil": ("South America", "South America"),
    "Argentina": ("South America", "South America"),
    "Chile": ("South America", "South America"),
    "Colombia": ("South America", "South America"),
    "Peru": ("South America", "South America"),
    "Ecuador": ("South America", "South America"),
    "Bolivia": ("South America", "South America"),
    # ===== Europe =====
    "Germany": ("Europe", "Western Europe"),
    "France": ("Europe", "Western Europe"),
    "Netherlands": ("Europe", "Western Europe"),
    "Belgium": ("Europe", "Western Europe"),
    "Luxembourg": ("Europe", "Western Europe"),
    "Switzerland": ("Europe", "Western Europe"),
    "Austria": ("Europe", "Western Europe"),
    "United Kingdom": ("Europe", "Northern Europe"),
    "Ireland": ("Europe", "Northern Europe"),
    "Sweden": ("Europe", "Northern Europe"),
    "Denmark": ("Europe", "Northern Europe"),
    "Finland": ("Europe", "Northern Europe"),
    "Estonia": ("Europe", "Northern Europe"),
    "Latvia": ("Europe", "Northern Europe"),
    "Lithuania": ("Europe", "Northern Europe"),
    "Jersey": ("Europe", "Northern Europe"),
    "Spain": ("Europe", "Southern Europe"),
    "Portugal": ("Europe", "Southern Europe"),
    "Italy": ("Europe", "Southern Europe"),
    "Greece": ("Europe", "Southern Europe"),
    "Cyprus": ("Europe", "Southern Europe"),
    "Malta": ("Europe", "Southern Europe"),
    "Andorra": ("Europe", "Southern Europe"),
    "Gibraltar": ("Europe", "Southern Europe"),
    "Slovenia": ("Europe", "Southern Europe"),
    "Croatia": ("Europe", "Southern Europe"),
    "Bosnia and Herzegovina": ("Europe", "Southern Europe"),
    "Serbia": ("Europe", "Southern Europe"),
    "Poland": ("Europe", "Eastern Europe"),
    "Czech Republic": ("Europe", "Eastern Europe"),
    "Romania": ("Europe", "Eastern Europe"),
    "Bulgaria": ("Europe", "Eastern Europe"),
    "Ukraine": ("Europe", "Eastern Europe"),
    "Russia": ("Europe", "Eastern Europe"),
    "Moldova": ("Europe", "Eastern Europe"),
    # ===== Africa =====
    "South Africa": ("Africa", "Sub-Saharan Africa"),
    "Nigeria": ("Africa", "Sub-Saharan Africa"),
    "Kenya": ("Africa", "Sub-Saharan Africa"),
    "Ghana": ("Africa", "Sub-Saharan Africa"),
    "Uganda": ("Africa", "Sub-Saharan Africa"),
    "Mauritius": ("Africa", "Sub-Saharan Africa"),
    "Central African Republic": ("Africa", "Sub-Saharan Africa"),
    "Egypt": ("Africa", "Northern Africa"),
    "Tunisia": ("Africa", "Northern Africa"),
    "Algeria": ("Africa", "Northern Africa"),
    # ===== Asia =====
    "India": ("Asia", "Southern Asia"),
    "Pakistan": ("Asia", "Southern Asia"),
    "Iran": ("Asia", "Southern Asia"),
    "China": ("Asia", "Eastern Asia"),
    "Japan": ("Asia", "Eastern Asia"),
    "South Korea": ("Asia", "Eastern Asia"),
    "Hong Kong": ("Asia", "Eastern Asia"),
    "Vietnam": ("Asia", "South-Eastern Asia"),
    "Thailand": ("Asia", "South-Eastern Asia"),
    "Singapore": ("Asia", "South-Eastern Asia"),
    "Malaysia": ("Asia", "South-Eastern Asia"),
    "Indonesia": ("Asia", "South-Eastern Asia"),
    "Philippines": ("Asia", "South-Eastern Asia"),
    "Saudi Arabia": ("Asia", "Western Asia"),
    "United Arab Emirates": ("Asia", "Western Asia"),
    "Qatar": ("Asia", "Western Asia"),
    "Kuwait": ("Asia", "Western Asia"),
    "Iraq": ("Asia", "Western Asia"),
    "Israel": ("Asia", "Western Asia"),
    "Turkey": ("Asia", "Western Asia"),
    "Armenia": ("Asia", "Western Asia"),
    "Georgia": ("Asia", "Western Asia"),
    "Uzbekistan": ("Asia", "Central Asia"),
    # ===== Oceania =====
    "Australia": ("Oceania", "Australia and New Zealand"),
    "New Zealand": ("Oceania", "Australia and New Zealand"),
    "American Samoa": ("Oceania", "Polynesia"),
}

UNKNOWN: tuple[str, str] = ("Other", "Other")


def lookup(country: str) -> tuple[str, str]:
    """Return (continent, region) for the given country, with fallback."""
    return COUNTRY_TO_REGION.get(country, UNKNOWN)
