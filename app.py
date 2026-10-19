
from flask import Flask, render_template, request, g
import json
import os
import threading
import time
import urllib.error
import urllib.request

app = Flask(__name__)

# --------------------------------------------------
# PREDICTOPS CONFIGURATION
# --------------------------------------------------

PREDICTOPS_URL = os.environ.get(
    "PREDICTOPS_URL",
    "http://127.0.0.1:5000/api/ingest"
)

PREDICTOPS_TOKEN = os.environ.get(
    "PREDICTOPS_INGEST_TOKEN",
    "local-demo-token"
)

# --------------------------------------------------
# EXISTING POKEMON DATA
# --------------------------------------------------

POKEMON = [
    ("Charizard", "Fire", "Flying", "charizard"),
    ("Gengar", "Ghost", "Poison", "gengar"),
    ("Gallade", "Psychic", "Fighting", "gallade"),
    ("Ceruledge", "Fire", "Ghost", "ceruledge"),
    ("Vaporeon", "Water", "", "vaporeon"),
    ("Giratina", "Ghost", "Dragon", "giratina"),
    ("Absol", "Dark", "", "absol"),
    ("Sableye", "Dark", "Ghost", "sableye"),
    ("Chien-Pao", "Dark", "Ice", "chien-pao"),
    ("Dragonite", "Dragon", "Flying", "dragonite"),
    ("Suicune", "Water", "", "suicune"),
    ("Thundurus", "Electric", "Flying", "thundurus"),
    ("Blaziken", "Fire", "Fighting", "blaziken"),
    ("Shiny Charizard", "Fire", "Flying", "charizard"),
    ("Xurkitree", "Electric", "", "xurkitree"),
    ("Tinkaton", "Fairy", "Steel", "tinkaton"),
    ("Charmander", "Fire", "", "charmander"),
]

SPRITES = {
    "charizard": "6",
    "gengar": "94",
    "gallade": "475",
    "ceruledge": "937",
    "vaporeon": "134",
    "giratina": "487",
    "absol": "359",
    "sableye": "302",
    "chien-pao": "1002",
    "dragonite": "149",
    "suicune": "245",
    "thundurus": "642",
    "blaziken": "257",
    "xurkitree": "796",
    "tinkaton": "959",
    "charmander": "4",
}

# --------------------------------------------------
# REQUEST TIMING
# --------------------------------------------------

@app.before_request
def start_request_timer():
    g.request_started_at = time.perf_counter()


# --------------------------------------------------
# SEND METRICS TO PREDICTOPS
# --------------------------------------------------

def send_metric_to_predictops(metric):
    """Send a blog request metric to PredictOps."""

    try:
        body = json.dumps(metric).encode("utf-8")

        req = urllib.request.Request(
            PREDICTOPS_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Monitor-Token": PREDICTOPS_TOKEN,
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=3) as response:
            response.read()

            if response.status != 202:
                print(
                    "PredictOps returned unexpected status:",
                    response.status,
                )

    except urllib.error.HTTPError as error:
        print(
            "PredictOps rejected the metric:",
            error.code,
            error.reason,
        )

    except Exception as error:
        print("Could not send metric to PredictOps:", error)


# --------------------------------------------------
# COLLECT BLOG REQUEST METRICS
# --------------------------------------------------

@app.after_request
def collect_request_metric(response):
    started = getattr(g, "request_started_at", None)

    # Avoid recording an ingestion request if this application
    # is later configured to expose the same endpoint.
    if started is not None and request.path != "/api/ingest":
        latency_ms = (
            time.perf_counter() - started
        ) * 1000

        metric = {
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 2),
            "route": request.path,
            "method": request.method,
            "client_ip": request.remote_addr or "unknown",

            # Placeholders only: these are not actual host readings.
            "cpu_percent": 0,
            "memory_percent": 0,
        }

        threading.Thread(
            target=send_metric_to_predictops,
            args=(metric,),
            daemon=True,
        ).start()

    return response


# --------------------------------------------------
# BLOG PAGES
# --------------------------------------------------

@app.get("/")
def home():
    return render_template("home.html")


@app.get("/about")
def about():
    return render_template("about.html")


@app.get("/pokemon")
def pokemon():
    entries = []

    for name, type1, type2, key in POKEMON:
        sprite_id = SPRITES.get(key, "25")

        if name == "Shiny Charizard":
            sprite = (
                "https://raw.githubusercontent.com/"
                "PokeAPI/sprites/master/sprites/pokemon/"
                f"shiny/{sprite_id}.png"
            )
        else:
            sprite = (
                "https://raw.githubusercontent.com/"
                "PokeAPI/sprites/master/sprites/pokemon/"
                f"{sprite_id}.png"
            )

        entries.append({
            "name": name,
            "type1": type1,
            "type2": type2,
            "sprite": sprite,
        })

    return render_template(
        "pokemon.html",
        pokemon=entries,
    )


@app.get("/blog")
def blog():
    # Preserve the existing Blog page and template.
    return render_template(
        "blank.html",
        page_title="Blog",
    )


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Frutiger Aero Blog",
    }


# --------------------------------------------------
# PERFORMANCE TEST ROUTES
# --------------------------------------------------

@app.get("/test/slow")
def test_slow():
    # Deliberately delay this response by 1.5 seconds.
    time.sleep(1.5)

    return "Slow response test completed", 200


@app.get("/test/error")
def test_error():
    # Deliberately return HTTP 500 for monitoring tests.
    return "Intentional server error test", 500


# --------------------------------------------------
# START BLOG SERVER
# --------------------------------------------------

if __name__ == "__main__":
    print("Frutiger Aero Blog: http://127.0.0.1:5001")
    print("Health check: http://127.0.0.1:5001/health")
    print("Slow test: http://127.0.0.1:5001/test/slow")
    print("Error test: http://127.0.0.1:5001/test/error")
    print("PredictOps target:", PREDICTOPS_URL)

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
    )
