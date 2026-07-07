# Ekwateur Billing for Home Assistant

A HACS custom integration that estimates your Ekwateur electricity/gas bill
locally in Home Assistant, using the flat per-kWh rates ported from the
reference [EkwateurBillingAPI](https://github.com/hichameaa/EkwateurBillingAPI)
Java project.

**This does not call any Ekwateur web service.** It has no network
connection to Ekwateur at all — that reference project doesn't either; it's a
standalone billing calculator, not a client of a real Ekwateur customer API.
This integration instead reads the consumption values from energy sensors
you already have in Home Assistant (e.g. a Linky/TIC sensor, a gas meter
sensor) and multiplies them by Ekwateur's published flat rates to produce
cost sensors.

## What it creates

For each configured client, up to three sensors:

- **Electricity cost** — `electricity_consumption_sensor (kWh) × electricity_rate`
- **Gas cost** — `gas_consumption_sensor (kWh) × gas_rate`
- **Total cost** — sum of the two

Sensors update immediately whenever the source consumption sensor updates
(no polling).

## Rates

Ported as-is from `util/BillingRates.java` in the reference project:

| Client type | Electricity €/kWh | Gas €/kWh |
|---|---|---|
| Individual | 0.121 | 0.115 |
| Professional, turnover ≤ €1M | 0.118 | 0.113 |
| Professional, turnover > €1M | 0.114 | 0.111 |

These are placeholder/demo rates from the reference project, not necessarily
your real Ekwateur contract rates — check your own contract and edit
`const.py` if needed.

## Installation

### Via HACS (custom repository)

1. HACS → the "⋮" menu → **Custom repositories**.
2. Add this repository's URL, category **Integration**.
3. Install "Ekwateur Billing", then restart Home Assistant.

### Manually

Copy `custom_components/ekwateur` into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

Settings → Devices & Services → Add Integration → **Ekwateur Billing**.

1. Choose **Individual** or **Professional**.
2. Enter your client reference (format `EKWxxxxxxxx`) and identity/company details.
3. Pick the HA sensor(s) that report your electricity and/or gas consumption
   in kWh (Wh and MWh are also accepted and auto-converted). At least one is
   required.

You can add multiple client configurations (e.g. one per property).
