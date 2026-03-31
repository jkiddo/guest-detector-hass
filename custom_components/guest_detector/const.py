"""Constants for the Guest Detector integration."""

DOMAIN = "guest_detector"

CONF_ENERGY_ENTITY = "energy_entity"
CONF_WINDOW_SIZE = "window_size"
CONF_THRESHOLD = "threshold"
CONF_MIN_EXCESS = "min_excess"
CONF_HEATING_FLOOR = "heating_floor"

DEFAULT_WINDOW_SIZE = 30
DEFAULT_THRESHOLD = 1.5
DEFAULT_MIN_EXCESS = 2.0
DEFAULT_HEATING_FLOOR = 3.0
DEFAULT_ENERGY_ENTITY = "sensor.eloverblik_energy_statistic"
