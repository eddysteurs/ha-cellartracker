"""Constants for the CellarTracker integration."""

from datetime import timedelta

DOMAIN = "cellartracker"

CONF_DOWNLOAD_LABELS = "download_labels"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=60)
DEFAULT_DOWNLOAD_LABELS = True

BASE_URL = "https://www.cellartracker.com"
XLQUERY_URL = f"{BASE_URL}/xlquery.asp"
WINE_URL = f"{BASE_URL}/wine.asp"

# Tables fetched every update. Inventory is required, Consumed is optional.
TABLE_INVENTORY = "Inventory"
TABLE_CONSUMED = "Consumed"

# Local folder (inside /config/www) for bottle images, served as /local/wine/
IMAGE_DIR = "wine"
LABEL_PREFIX = "ct_"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

# Label download limits (be gentle with cellartracker.com)
LABELS_PER_UPDATE = 5
LABEL_RETRY_DAYS = 30

# How many consumed bottles to keep in the sensor attribute
CONSUMED_LIMIT = 250
