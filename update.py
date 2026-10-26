"""Daily data pipeline for Cosmic Circuit Daily.

Sources: NASA APOD, arXiv Atom API, Open-Meteo forecast API.
Quantum experiment: real PennyLane simulation on default.qubit.
"""
from __future__ import annotations
import json, math, os, random, re, sys, time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET
import requests

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
DATA_PATH = ROOT / "data.json"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "CosmicCircuitDaily/1.0 (educational science dashboard)"})


def load_config():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    # Optional environment overrides make GitHub Actions configuration easy.
    if os.getenv("WEATHER_CITY"):
        cfg["weather"]["city"] = os.environ["WEATHER_CITY"]
    if os.getenv("WEATHER_LATITUDE"):
        cfg["weather"]["latitude"] = float(os.environ["WEATHER_LATITUDE"])
    if os.getenv("WEATHER_LONGITUDE"):
        cfg["weather"]["longitude"] = float(os.environ["WEATHER_LONGITUDE"])
    return cfg


def get_json(url, params=None, timeout=20):
    response = SESSION.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_text(url, params=None, timeout=20):
    response = SESSION.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.text


def safe_date(value):
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except Exception:
        return str(value)[:10]


def fetch_apod(timeout):
    """NASA Astronomy Picture of the Day. DEMO_KEY is a shared, rate-limited key."""
    key = os.getenv("NASA_API_KEY") or "DEMO_KEY"
    item = get_json("https://api.nasa.gov/planetary/apod", {"api_key": key}, timeout)
    return [{
        "id": "nasa-apod-" + item.get("date", datetime.now(timezone.utc).date().isoformat()),
        "title": item.get("title", "Astronomy Picture of the Day"),
        "summary": item.get("explanation", "NASA's daily astronomy feature."),
        "url": item.get("url", "https://apod.nasa.gov/apod/astropix.html"),
        "image": item.get("url", "") if item.get("media_type") == "image" else item.get("thumbnail_url", ""),
        "date": item.get("date", ""), "source": "NASA APOD", "topic": "astro",
        "kind": item.get("media_type", "image")
    }]


def fetch_arxiv(search_query, topic, label, max_items, timeout):
    """Use arXiv's public Atom API rather than scraping result pages."""
    raw = get_text("https://export.arxiv.org/api/query", {
        "search_query": search_query, "start": 0, "max_results": max_items,
        "sortBy": "submittedDate", "sortOrder": "descending"
    }, timeout)
    root = ET.fromstring(raw)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    records = []
    for entry in root.findall("a:entry", ns):
        title = re.sub(r"\s+", " ", entry.findtext("a:title", default="", namespaces=ns).strip())
        abstract = re.sub(r"\s+", " ", entry.findtext("a:summary", default="", namespaces=ns).strip())
        url = entry.findtext("a:id", default="", namespaces=ns)
        published = entry.findtext("a:published", default="", namespaces=ns)[:10]
        if not title or not url:
            continue
        authors = [a.findtext("a:name", default="", namespaces=ns) for a in entry.findall("a:author", ns)]
        records.append({
            "id": url.rstrip("/").split("/")[-1], "title": title,
            "summary": abstract, "url": url, "image": "", "date": published,
            "source": label, "topic": topic, "authors": [x for x in authors if x][:4], "kind": "paper"
        })
    return records


def fetch_weather(cfg, timeout):
    w = cfg["weather"]
    data = get_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": w["latitude"], "longitude": w["longitude"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
        "forecast_days": 3, "timezone": w.get("timezone", "auto")
    }, timeout)
    current = data.get("current", {})
    daily = data.get("daily", {})
    hourly = data.get("hourly", {})
    return {
        "location": {"city": w["city"], "country": w["country"], "latitude": w["latitude"], "longitude": w["longitude"]},
        "current": current,
        "current_label": weather_label(current.get("weather_code")),
        "daily": daily, "hourly": hourly,
        "source": "Open-Meteo", "url": "https://open-meteo.com/",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


def weather_label(code):
    labels = {0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",48:"Depositing rime fog",51:"Light drizzle",53:"Drizzle",55:"Dense drizzle",56:"Freezing drizzle",57:"Heavy freezing drizzle",61:"Light rain",63:"Rain",65:"Heavy rain",66:"Freezing rain",67:"Heavy freezing rain",71:"Light snow",73:"Snow",75:"Heavy snow",77:"Snow grains",80:"Rain showers",81:"Rain showers",82:"Violent rain showers",85:"Snow showers",86:"Heavy snow showers",95:"Thunderstorm",96:"Thunderstorm with hail",99:"Severe thunderstorm"}
    try: return labels.get(int(code), "Conditions unavailable")
    except (TypeError, ValueError): return "Conditions unavailable"


def run_pennylane_experiment(day):
    """Run a real PennyLane simulator circuit; date changes the experiment angle."""
    import pennylane as qml
    seed = int(day.replace("-", ""))
    rng = random.Random(seed)
    theta = 0.25 + rng.random() * 1.1
    dev = qml.device("default.qubit", wires=2, shots=1000, seed=seed % (2**32 - 1))

    @qml.qnode(dev)
    def circuit(angle):
        qml.RY(angle, wires=0)
        qml.Hadamard(wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RZ(0.35, wires=1)
        return qml.probs(wires=[0, 1]), qml.expval(qml.PauliZ(0))

    probabilities, z_expectation = circuit(theta)
    probabilities = [round(float(x), 4) for x in probabilities]
    # PennyLane draws the actual circuit; this is instructional metadata, not a hardware claim.
    diagram = qml.draw(circuit)(theta)
    return {
        "engine": "PennyLane", "device": "default.qubit", "mode": "classical simulation of a quantum circuit",
        "title": "Two-qubit entanglement experiment", "date": day,
        "description": "Prepare a parameterized qubit, apply a Hadamard gate, entangle the pair with CNOT, then estimate basis-state probabilities and the Pauli-Z expectation value.",
        "theta_radians": round(theta, 4), "shots": 1000,
        "basis_states": ["|00⟩", "|01⟩", "|10⟩", "|11⟩"],
        "probabilities": probabilities, "z_expectation": round(float(z_expectation), 4),
        "circuit_text": diagram, "source": "PennyLane simulator", "url": "https://pennylane.ai/"
    }


def dedupe(items):
    seen, result = set(), []
    for item in items:
        key = (item.get("url") or item.get("title", "")).lower().rstrip("/")
        if key and key not in seen:
            seen.add(key); result.append(item)
    return result


def build_brief(astro, quantum, weather):
    bits = []
    if astro: bits.append(f"Space watch: {astro[0]['title']}")
    if quantum: bits.append(f"Quantum watch: {quantum[0]['title']}")
    if weather:
        c = weather.get("current", {})
        temp = c.get("temperature_2m")
        place = weather.get("location", {}).get("city", "your configured location")
        if temp is not None: bits.append(f"Weather in {place}: {temp}°C, {weather.get('current_label', 'conditions available').lower()}.")
    return bits or ["The dashboard is ready; some live sources could not be reached during this update."]


def main():
    cfg = load_config(); timeout = int(cfg.get("request_timeout_seconds", 20)); max_items = int(cfg.get("max_items_per_topic", 8))
    today = datetime.now(timezone.utc).date().isoformat()
    previous = {}
    if DATA_PATH.exists():
        try: previous = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except Exception: pass
    errors = []
    source_status = {"nasa_apod": False, "arxiv_astro": False, "arxiv_quantum": False, "weather": False, "pennylane": False}
    astro, quantum, weather = [], [], None
    tasks = [
        ("NASA APOD", lambda: fetch_apod(timeout), "astro"),
        ("Astrophysics papers", lambda: fetch_arxiv("cat:astro-ph.*", "astro", "arXiv astrophysics", max_items, timeout), "astro"),
        ("Quantum papers", lambda: fetch_arxiv("cat:quant-ph", "quantum", "arXiv quant-ph", max_items, timeout), "quantum"),
        ("Weather", lambda: fetch_weather(cfg, timeout), "weather")
    ]
    for label, fn, kind in tasks:
        try:
            value = fn()
            if kind == "astro":
                astro.extend(value)
                source_status["nasa_apod" if label == "NASA APOD" else "arxiv_astro"] = bool(value)
            elif kind == "quantum":
                quantum.extend(value)
                source_status["arxiv_quantum"] = bool(value)
            else:
                weather = value
                source_status["weather"] = True
            print(f"OK {label}: " + (str(len(value)) + " records" if isinstance(value, list) else "updated"))
        except Exception as exc:
            errors.append({"source": label, "error": f"{type(exc).__name__}: {exc}"})
            print(f"WARN {label}: {type(exc).__name__}: {exc}")
    astro = dedupe(astro)[:max_items + 1]
    quantum = dedupe(quantum)[:max_items]
    fresh_data_available = bool(astro or quantum or weather)
    try:
        experiment = run_pennylane_experiment(today)
        source_status["pennylane"] = True
        print("OK PennyLane experiment: simulated 2-qubit circuit")
    except Exception as exc:
        # A missing PennyLane install is a hard failure, not a fake result.
        print(f"ERROR PennyLane experiment failed: {exc}", file=sys.stderr)
        raise
    # Preserve last good data if a source has a temporary outage.
    if not astro: astro = previous.get("astro", [])
    if not quantum: quantum = previous.get("quantum", [])
    if weather is None: weather = previous.get("weather")
    data = {
        "schema_version": 1, "updated_at": datetime.now(timezone.utc).isoformat(),
        "generated_for_date": today, "status": "partial" if errors else "ok",
        "astro": astro, "quantum": quantum, "weather": weather,
        "pennylane": experiment, "daily_brief": build_brief(astro, quantum, weather),
        "source_status": source_status,
        "errors": errors
    }
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DATA_PATH.name}: astro={len(astro)}, quantum={len(quantum)}, weather={bool(weather)}")
    if not fresh_data_available:
        raise RuntimeError("All live data sources failed; preserved previous data where available, but this refresh produced no fresh source data.")

if __name__ == "__main__":
    main()
