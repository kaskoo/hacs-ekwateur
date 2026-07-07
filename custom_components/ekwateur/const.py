"""Constants for the Ekwateur Billing integration."""
from __future__ import annotations

from decimal import Decimal

DOMAIN = "ekwateur"

CONF_CLIENT_CATEGORY = "client_category"
CONF_CLIENT_REFERENCE = "client_reference"
CONF_CIVILITY = "civility"
CONF_FIRST_NAME = "first_name"
CONF_LAST_NAME = "last_name"
CONF_CORPORATE_NAME = "corporate_name"
CONF_SIRET = "siret"
CONF_PRO_CLIENT_TYPE = "pro_client_type"
CONF_ELECTRICITY_SENSOR = "electricity_sensor"
CONF_GAS_SENSOR = "gas_sensor"

CLIENT_CATEGORY_INDIVIDUAL = "individual"
CLIENT_CATEGORY_PRO = "pro"

PRO_TYPE_HIGH_TURNOVER = "high_turnover"
PRO_TYPE_LOW_TURNOVER = "low_turnover"

CIVILITY_M = "m"
CIVILITY_MME = "mme"
CIVILITY_MLLE = "mlle"

# Mirrors BillingServiceImpl.CLIENT_REFERENCE_REGEX from the reference Java project.
CLIENT_REFERENCE_REGEX = r"^EKW\d{8}$"

# €/kWh rates, ported verbatim from util/BillingRates.java in the reference project.
RATE_ELECTRICITY_INDIVIDUAL = Decimal("0.121")
RATE_GAS_INDIVIDUAL = Decimal("0.115")
RATE_ELECTRICITY_PRO_HIGH_TURNOVER = Decimal("0.114")
RATE_GAS_PRO_HIGH_TURNOVER = Decimal("0.111")
RATE_ELECTRICITY_PRO_LOW_TURNOVER = Decimal("0.118")
RATE_GAS_PRO_LOW_TURNOVER = Decimal("0.113")


def get_rates(client_category: str, pro_client_type: str | None) -> tuple[Decimal, Decimal]:
    """Return (electricity_rate, gas_rate) for a given client configuration."""
    if client_category == CLIENT_CATEGORY_INDIVIDUAL:
        return RATE_ELECTRICITY_INDIVIDUAL, RATE_GAS_INDIVIDUAL
    if pro_client_type == PRO_TYPE_HIGH_TURNOVER:
        return RATE_ELECTRICITY_PRO_HIGH_TURNOVER, RATE_GAS_PRO_HIGH_TURNOVER
    return RATE_ELECTRICITY_PRO_LOW_TURNOVER, RATE_GAS_PRO_LOW_TURNOVER
