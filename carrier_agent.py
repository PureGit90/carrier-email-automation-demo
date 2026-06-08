"""
carrier_agent.py

Claude API carrier-matching logic for the auto-transport brokerage.
Reads carrier CSV, sends route + carrier list to Claude, returns matched carriers as JSON.
"""

import os
import json
import anthropic
import pandas as pd

SYSTEM_PROMPT = (
    "You are a carrier-matching agent for an auto-transport brokerage. "
    "Given a route (pickup state/region derived from ZIP, delivery state/region, vehicle type) "
    "and a carrier list CSV, identify the best matching carriers. "
    "Consider: their covered regions include both origin and destination states, "
    "their vehicle types include the requested vehicle type. "
    "Return JSON only: "
    '{\"matched_carriers\": [{\"name\": \"...\", \"email\": \"...\", \"phone\": \"...\", \"reason\": \"...\"}]}'
)

# Simple ZIP → state lookup (sample; production would use a real ZIP database)
ZIP_STATE_MAP = {
    "77": "TX", "78": "TX", "79": "TX",
    "70": "LA", "71": "LA",
    "73": "OK", "74": "OK",
    "72": "AR",
    "33": "FL", "34": "FL", "32": "FL",
    "30": "GA", "31": "GA",
    "90": "CA", "91": "CA", "92": "CA", "93": "CA", "94": "CA", "95": "CA",
    "85": "AZ", "86": "AZ",
    "80": "CO", "81": "CO",
    "60": "IL", "61": "IL", "62": "IL",
    "10": "NY", "11": "NY", "12": "NY", "13": "NY", "14": "NY",
    "07": "NJ", "08": "NJ",
    "02": "MA",
    "40": "KY", "41": "KY", "42": "KY",
    "38": "TN", "37": "TN",
    "39": "MS",
    "35": "AL", "36": "AL",
    "87": "NM", "88": "NM",
    "84": "UT",
    "97": "OR", "98": "WA",
    "59": "MT",
    "82": "WY",
    "55": "MN",
    "68": "NE", "69": "NE",
    "66": "KS", "67": "KS",
    "63": "MO", "64": "MO", "65": "MO",
    "50": "IA", "51": "IA",
    "57": "SD",
    "58": "ND",
    "53": "WI", "54": "WI",
    "48": "MI", "49": "MI",
    "43": "OH", "44": "OH", "45": "OH",
    "46": "IN", "47": "IN",
    "15": "PA", "16": "PA", "17": "PA", "18": "PA", "19": "PA",
    "20": "MD", "21": "MD",
    "22": "VA", "23": "VA", "24": "VA",
    "25": "WV", "26": "WV", "27": "NC", "28": "NC",
    "29": "SC",
    "19": "DE",
    "06": "CT",
    "03": "NH",
    "05": "VT",
    "04": "ME",
    "89": "NV",
    "96": "HI",
    "99": "AK",
}


def zip_to_state(zip_code: str) -> str:
    """Derive US state abbreviation from ZIP code prefix."""
    if not zip_code:
        return "UNKNOWN"
    prefix2 = zip_code[:2]
    prefix3 = zip_code[:3]
    return ZIP_STATE_MAP.get(prefix2, ZIP_STATE_MAP.get(prefix3, "UNKNOWN"))


def load_carriers(csv_path: str) -> str:
    """Load carrier CSV and return as a compact string for the prompt."""
    df = pd.read_csv(csv_path)
    return df.to_csv(index=False)


def match_carriers(
    pickup_zip: str,
    delivery_zip: str,
    vehicle_type: str,
    csv_path: str,
    api_key: str | None = None,
) -> dict:
    """
    Call Claude to match carriers for a given route.

    Returns:
        dict with keys:
            - matched_carriers: list of {name, email, phone, reason}
            - pickup_state: derived state
            - delivery_state: derived state
            - error: str or None
    """
    pickup_state = zip_to_state(pickup_zip)
    delivery_state = zip_to_state(delivery_zip)

    carriers_csv = load_carriers(csv_path)

    user_message = (
        f"Route details:\n"
        f"- Pickup ZIP: {pickup_zip} (state: {pickup_state})\n"
        f"- Delivery ZIP: {delivery_zip} (state: {delivery_state})\n"
        f"- Vehicle type: {vehicle_type}\n\n"
        f"Carrier list (CSV):\n{carriers_csv}\n\n"
        f"Return only JSON matching the schema described in your instructions."
    )

    resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not resolved_key:
        return {
            "matched_carriers": [],
            "pickup_state": pickup_state,
            "delivery_state": delivery_state,
            "error": "ANTHROPIC_API_KEY not set",
        }

    try:
        client = anthropic.Anthropic(api_key=resolved_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(
                line for line in lines if not line.startswith("```")
            ).strip()

        parsed = json.loads(raw)
        return {
            "matched_carriers": parsed.get("matched_carriers", []),
            "pickup_state": pickup_state,
            "delivery_state": delivery_state,
            "error": None,
        }

    except json.JSONDecodeError as exc:
        return {
            "matched_carriers": [],
            "pickup_state": pickup_state,
            "delivery_state": delivery_state,
            "error": f"JSON parse error: {exc}. Raw response: {raw[:300]}",
        }
    except anthropic.APIError as exc:
        return {
            "matched_carriers": [],
            "pickup_state": pickup_state,
            "delivery_state": delivery_state,
            "error": f"Anthropic API error: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "matched_carriers": [],
            "pickup_state": pickup_state,
            "delivery_state": delivery_state,
            "error": f"Unexpected error: {exc}",
        }
