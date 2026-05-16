# Apify Fuel Price

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://docs.python.org/3.12/)
[![Apify](https://img.shields.io/badge/platform-Apify-00A2E0?logo=apify&logoColor=white)](https://apify.com/)

**Apify Actor (Python)** for **national average** unleaded petrol and diesel prices. **The United Kingdom is supported today**; the codebase is structured so **more countries can be added** without breaking the API. Includes a **1-hour cache** (named key-value store) and a **compact JSON** row on the default dataset with **explicit currency and volume unit** so values are never ambiguous (e.g. litre vs gallon).

---

## Table of contents

- [Why this exists](#why-this-exists)
- [Features](#features)
- [Roadmap](#roadmap)
- [Requirements](#requirements)
- [Deploy on Apify](#deploy-on-apify)
- [Input](#input)
- [Output (default dataset)](#output-default-dataset)
- [Data sources](#data-sources)
- [Caching](#caching)
- [Local development](#local-development)
- [Testing](#testing)
- [Disclaimer](#disclaimer)
- [License](#license)
- [References](#references)

---

## Why this exists

Fuel price averages move often. This Actor gives you a **small, stable JSON** payload suitable for dashboards, alerts, or downstream pipelines—without running a browser—by reading the same public pages and sheet endpoints a normal visitor would hit.

---

## Features

- **Multi-country direction:** built to support **more countries over time**; **only `uk` is wired today** (see [`SUPPORTED_COUNTRIES`](src/config.py) and fetchers under `src/fetchers/`).
- **Pricing contract:** each supported country has its own ISO **`currency`** and **`volumeUnit`**; **`petrol`** and **`diesel`** are always that currency's **major unit** per that volume (no cents/pence field—local quoting is normalized in code). **UK today:** sources use pence/litre; output is pounds per litre with `currency: GBP`.
- **Case-insensitive input:** `uk`, `UK`, `Uk`, etc. (validated in [`.actor/input_schema.json`](.actor/input_schema.json)).
- **Upstream HTTP:** each GET uses a **10 second** timeout ([`src/config.py`](src/config.py)); UK fallback **fetches both gviz endpoints in parallel** so each request is still bounded by that timeout.
- **Resilient fetch:** primary HTML from [PetrolPrices.co.uk](https://petrolprices.co.uk/uk-fuel-prices-live.php), fallback to public **Google Visualization** JSON used by [PetrolPrices.com](https://www.petrolprices.com/latest-fuel-price-data-across-the-uk/).
- **Cache:** 1-hour TTL in a **named** key-value store (see [Caching](#caching)); **no cache metadata** in the dataset row (TTL uses `fetchedAt` in KV only).
- **Docker:** [`Dockerfile`](Dockerfile) based on [`apify/actor-python:3.12`](https://docs.apify.com/sdk/python/docs/overview) for parity with Apify Cloud.

---

## Roadmap

- **Near term:** add more `country` values, fetchers, and [`COUNTRY_OUTPUT_PRICING`](src/config.py) entries (`currency` + `volumeUnit`); extend `_parsed_to_output_record` in [`src/services/fuel_service.py`](src/services/fuel_service.py) so each locale normalizes to major currency per volume.
- **Input schema:** will gain new `enum` / `pattern` values as countries ship; today it only accepts UK codes.

---

## Requirements

| Context | Notes |
|---------|--------|
| **Apify Cloud** | Matches the Dockerfile (Python 3.12). |
| **Local `python -m src.main`** | **Python 3.10+** recommended (Apify SDK / Crawlee expectations). |
| **Tests** | Parser tests are offline. **Live HTTP** tests need network (see [Testing](#testing)). |

Optional: [Apify CLI](https://docs.apify.com/cli) for `apify run` / deploy workflows.

---

## Deploy on Apify

1. Push this repository to GitHub (or upload the project).
2. In [Apify Console](https://console.apify.com/), create an Actor from the Git repository (or `apify push` if you use the CLI).
3. Set **build** to use the root [`Dockerfile`](Dockerfile) and run with default memory as needed.

After the first run, inspect the **default dataset** for the JSON row described below.

---

## Input

Defined in [`.actor/input_schema.json`](.actor/input_schema.json) (validated by Apify before the run starts).

| Field | Type | Description |
|-------|------|-------------|
| `country` | string | **UK today**; more countries planned. Case-insensitive (`uk`, `UK`, …). Pattern: `^[Uu][Kk]$`. |

---

## Output (default dataset)

Apify Console **Output** tab and API run `output` links are driven by [`.actor/output_schema.json`](.actor/output_schema.json); dataset field metadata and the results table use [`.actor/dataset_schema.json`](.actor/dataset_schema.json) ([output schema](https://docs.apify.com/platform/actors/development/actor-definition/output-schema), [dataset schema](https://docs.apify.com/platform/actors/development/actor-definition/dataset-schema)).

Each **successful** run appends **one object** to the **default dataset**.

| Field | Type | Description |
|-------|------|-------------|
| `country` | string | Normalized lowercase code (`uk` today). |
| `petrol` | number | National average unleaded: **major unit** of `currency` per `volumeUnit`. |
| `diesel` | number | National average diesel, same units as `petrol`. |
| `currency` | string | ISO 4217 code for how to read the two prices (e.g. UK **`GBP`**, future regions their own code). |
| `volumeUnit` | string | Volume basis for the “per” price (UK: **`litre`**). |
| `lastUpdate` | string | ISO-8601 UTC: upstream “last updated” when parseable, otherwise the fetch time. |

**Convention:** `petrol` and `diesel` use the **major ISO 4217 unit** of `currency` per `volumeUnit` (e.g. GBP as pounds, USD as dollars—not pence or cents as the numeric scale). Each country's pipeline converts local quoting to that scale. **UK:** public sources use pence/litre; the Actor outputs **pounds per litre** with `currency: GBP`.

**Caching:** TTL bookkeeping uses a `fetchedAt` field **only inside the named key-value store**, not in the dataset payload.

**Errors:** On failure you may still get **one** dataset item with `error`, `message`, and `country`, and the run is marked failed.

---

## Data sources

1. **Primary:** [PetrolPrices.co.uk — UK Fuel Prices Live](https://petrolprices.co.uk/uk-fuel-prices-live.php) (HTML; includes “Data feed last updated”).
2. **Fallback:** Public `gviz/tq` JSON for the same spreadsheet surfaced on [PetrolPrices.com — Latest fuel price data](https://www.petrolprices.com/latest-fuel-price-data-across-the-uk/).

No headless browser in v1. If both paths break, consider a Playwright-based fallback in a future version.

---

## Caching

| Item | Value |
|------|--------|
| **Store name** | `fuel-price-actor-cache` (see [`src/config.py`](src/config.py)) |
| **Key** | `fuel_avg_<country>` (e.g. `fuel_avg_uk`) |
| **TTL** | 1 hour, enforced in [`src/cache.py`](src/cache.py) |

The named store is shared across runs for your Apify account (unlike an ephemeral default store per run).

---

## Local development

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `storage/key_value_stores/default/INPUT.json`:

```json
{ "country": "UK" }
```

Run the Actor (Python **3.10+** locally; otherwise use Apify Cloud / Docker):

```bash
python -m src.main
```

Results are written under `storage/datasets/default/`. To reset local storages when using the Apify CLI:

```bash
apify run --purge
```

---

## Testing

```bash
pytest -v
```

- **Default run** includes **live HTTP** tests in [`tests/test_integration_live.py`](tests/test_integration_live.py) (marked `integration`, **network required**).
- **Offline / CI:** GitHub Actions runs `pytest -v -m "not integration"`. Locally you can do the same if you are offline.

```bash
pytest -v -m "not integration"
```

Print live responses:

```bash
pytest -v -s tests/test_integration_live.py
```

Print the **exact dataset JSON shape** (fixture-based, offline):

```bash
pytest -v -s tests/test_actor_output_contract.py
```

---

## Disclaimer

This project **reads publicly available** pages and sheet endpoints. You are responsible for complying with **terms of use**, **robots.txt**, and **applicable law** where you run the Actor. The software is provided **as-is**; average prices and upstream markup can change at any time. This repository is **not** affiliated with PetrolPrices.co.uk, PetrolPrices.com, or any other websites.

---

## License

This project is released under the **[MIT License](https://opensource.org/licenses/MIT)**. The full legal text is in [`LICENSE`](LICENSE).

---

## References

- [Apify SDK for Python — Overview](https://docs.apify.com/sdk/python/docs/overview)
- [Actor input schema specification](https://docs.apify.com/platform/actors/development/actor-definition/input-schema/specification/v1)
