"""Config flow for the Ekwateur Billing integration."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CIVILITY_M,
    CIVILITY_MLLE,
    CIVILITY_MME,
    CLIENT_CATEGORY_INDIVIDUAL,
    CLIENT_CATEGORY_PRO,
    CLIENT_REFERENCE_REGEX,
    CONF_CIVILITY,
    CONF_CLIENT_CATEGORY,
    CONF_CLIENT_REFERENCE,
    CONF_CORPORATE_NAME,
    CONF_ELECTRICITY_SENSOR,
    CONF_FIRST_NAME,
    CONF_GAS_SENSOR,
    CONF_LAST_NAME,
    CONF_PRO_CLIENT_TYPE,
    CONF_SIRET,
    DOMAIN,
    PRO_TYPE_HIGH_TURNOVER,
    PRO_TYPE_LOW_TURNOVER,
)

_CLIENT_REFERENCE_RE = re.compile(CLIENT_REFERENCE_REGEX)


def _sensor_selector() -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain="sensor"))


def _validate_common(user_input: dict[str, Any], errors: dict[str, str]) -> None:
    if not _CLIENT_REFERENCE_RE.match(user_input[CONF_CLIENT_REFERENCE]):
        errors[CONF_CLIENT_REFERENCE] = "invalid_client_reference"
    if not user_input.get(CONF_ELECTRICITY_SENSOR) and not user_input.get(CONF_GAS_SENSOR):
        errors["base"] = "no_sensor_selected"


class EkwateurConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ekwateur Billing."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick a client category, then branch to the matching step."""
        if user_input is not None:
            if user_input[CONF_CLIENT_CATEGORY] == CLIENT_CATEGORY_INDIVIDUAL:
                return await self.async_step_individual()
            return await self.async_step_pro()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CLIENT_CATEGORY, default=CLIENT_CATEGORY_INDIVIDUAL
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[CLIENT_CATEGORY_INDIVIDUAL, CLIENT_CATEGORY_PRO],
                        translation_key=CONF_CLIENT_CATEGORY,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_individual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure an individual (particulier) client."""
        errors: dict[str, str] = {}
        if user_input is not None:
            _validate_common(user_input, errors)
            if not errors:
                await self.async_set_unique_id(user_input[CONF_CLIENT_REFERENCE])
                self._abort_if_unique_id_configured()
                data = {CONF_CLIENT_CATEGORY: CLIENT_CATEGORY_INDIVIDUAL, **user_input}
                title = f"{user_input[CONF_FIRST_NAME]} {user_input[CONF_LAST_NAME]}"
                return self.async_create_entry(title=title, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_REFERENCE): str,
                vol.Required(CONF_CIVILITY, default=CIVILITY_M): SelectSelector(
                    SelectSelectorConfig(
                        options=[CIVILITY_M, CIVILITY_MME, CIVILITY_MLLE],
                        translation_key=CONF_CIVILITY,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_FIRST_NAME): str,
                vol.Required(CONF_LAST_NAME): str,
                vol.Optional(CONF_ELECTRICITY_SENSOR): _sensor_selector(),
                vol.Optional(CONF_GAS_SENSOR): _sensor_selector(),
            }
        )
        return self.async_show_form(step_id="individual", data_schema=schema, errors=errors)

    async def async_step_pro(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a professional client."""
        errors: dict[str, str] = {}
        if user_input is not None:
            _validate_common(user_input, errors)
            if not errors:
                await self.async_set_unique_id(user_input[CONF_CLIENT_REFERENCE])
                self._abort_if_unique_id_configured()
                data = {CONF_CLIENT_CATEGORY: CLIENT_CATEGORY_PRO, **user_input}
                return self.async_create_entry(title=user_input[CONF_CORPORATE_NAME], data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_REFERENCE): str,
                vol.Required(CONF_CORPORATE_NAME): str,
                vol.Required(CONF_SIRET): str,
                vol.Required(
                    CONF_PRO_CLIENT_TYPE, default=PRO_TYPE_LOW_TURNOVER
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[PRO_TYPE_LOW_TURNOVER, PRO_TYPE_HIGH_TURNOVER],
                        translation_key=CONF_PRO_CLIENT_TYPE,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_ELECTRICITY_SENSOR): _sensor_selector(),
                vol.Optional(CONF_GAS_SENSOR): _sensor_selector(),
            }
        )
        return self.async_show_form(step_id="pro", data_schema=schema, errors=errors)
