"""
Generates the human-readable "why" behind each schedule decision.

Uses Groq's OpenAI-compatible chat completions API when GROQ_API_KEY is set
(https://console.groq.com - free tier, no credit card). Falls back to a
deterministic template so the app works fully with zero API keys.
"""
import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def _fallback_reasoning(farm_name: str, crop: str, decision: dict, weather: dict) -> str:
    if decision["status"] == "Auto Skipped":
        return (
            f"{farm_name} irrigation has been postponed because "
            f"{weather.get('precipitation_mm', 0):.0f} mm of rainfall is expected "
            f"with a {weather.get('rain_probability', 0):.0f}% chance, which should "
            f"meet the crop's water needs without additional irrigation."
        )
    parts = [f"{farm_name} ({crop}) is scheduled for irrigation because"]
    reasons = []
    if decision.get("soil_moisture_low"):
        reasons.append("soil moisture is below the optimal threshold for this growth stage")
    if weather.get("temp_max", 0) >= 33:
        reasons.append("temperatures are expected to rise, increasing evapotranspiration")
    if weather.get("rain_probability", 0) < 30:
        reasons.append("no significant rainfall is forecast")
    if not reasons:
        reasons.append("scheduled water requirement has been reached for this stage")
    text = ", ".join(reasons)
    return (
        f"{parts[0]} {text}. Early morning irrigation reduces evaporation losses and "
        f"minimizes plant stress. Confidence: {decision.get('confidence_score', 0.85):.0%}."
    )


def generate_reasoning(farm_name: str, crop: str, growth_stage: str, decision: dict,
                        weather: dict, disease_risk: str = "low") -> str:
    if not GROQ_API_KEY:
        return _fallback_reasoning(farm_name, crop, decision, weather)

    prompt = (
        f"You are an irrigation scheduling AI. Explain in 2-3 concise sentences why the "
        f"following irrigation decision was made. Be specific and factual, no fluff.\n\n"
        f"Farm: {farm_name}\nCrop: {crop}\nGrowth stage: {growth_stage}\n"
        f"Decision: {decision.get('status')}\n"
        f"Water quantity: {decision.get('water_quantity_mm', 0)} mm\n"
        f"Soil moisture flag (low={decision.get('soil_moisture_low')})\n"
        f"Forecast: max temp {weather.get('temp_max')}C, "
        f"rain probability {weather.get('rain_probability')}%, "
        f"expected precipitation {weather.get('precipitation_mm')} mm, "
        f"humidity {weather.get('humidity')}%\n"
        f"Disease risk: {disease_risk}\n"
    )
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 200,
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content if content else _fallback_reasoning(farm_name, crop, decision, weather)
    except (requests.RequestException, KeyError, IndexError):
        return _fallback_reasoning(farm_name, crop, decision, weather)


def parse_voice_command(text: str, farms: list[dict]) -> dict:
    """Returns {intent, farm_id, date_hint, response_text}. Uses Groq for NLU when
    available; otherwise a simple keyword-based parser covering the documented
    command set (English keywords always recognized; Tamil/Hindi phrases work
    automatically once GROQ_API_KEY is set)."""
    if GROQ_API_KEY:
        farm_list = ", ".join(f"{f['id']}:{f['name']}" for f in farms)
        prompt = (
            "Parse this farmer voice command into JSON only, no prose. "
            'Schema: {"intent": one of '
            '["schedule_irrigation","postpone","show_schedule","cancel_irrigation",'
            '"next_irrigation","unknown"], "farm_id": int or null, '
            '"response_text": "short natural reply in the same language as the command"}. '
            f"Known farms (id:name): {farm_list}. "
            f'Command: "{text}"'
        )
        try:
            resp = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"},
                },
                timeout=15,
            )
            resp.raise_for_status()
            import json
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except requests.RequestException as e:
            print(f"Groq API request failed: {e}")
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Groq API response parsing failed: {e}")
        # fall through to keyword parser on any error

    lowered = text.lower()
    farm_id = None
    for f in farms:
        if f["name"].split(" - ")[0].lower() in lowered or f["crop_type"].lower() in lowered:
            farm_id = f["id"]
            break

    if "postpone" in lowered or "delay" in lowered:
        intent = "postpone"
        response = "Okay, I've postponed the irrigation as requested."
    elif "cancel" in lowered or "skip" in lowered:
        intent = "cancel_irrigation"
        response = "Irrigation has been cancelled."
    elif "next" in lowered and "irrigation" in lowered:
        intent = "next_irrigation"
        response = "Let me check your next scheduled irrigation."
    elif "show" in lowered or "what" in lowered:
        intent = "show_schedule"
        response = "Here is the schedule you asked for."
    elif "schedule" in lowered or "irrigate" in lowered:
        intent = "schedule_irrigation"
        response = "I've scheduled irrigation as requested."
    else:
        intent = "unknown"
        response = "Sorry, I didn't understand that command. Try: 'Schedule irrigation for tomorrow.'"

    return {"intent": intent, "farm_id": farm_id, "response_text": response}
