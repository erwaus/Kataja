#!/usr/bin/env python3
"""
Kataja Basket - tiedonhakuskripti
Hakee tulokset ja sarjataulukko-tiedot basket.fi:stä ja Flashscoresta
sekä tallentaa ne data/data.json tiedostoon jota HTML-sivu käyttää.
"""

import json
import os
import re
from datetime import datetime, timezone
import urllib.request
import urllib.error

# ── Apufunktiot ──────────────────────────────────────────────────────────────

def fetch(url, timeout=15):
    """Hakee URL:n sisällön. Palauttaa None jos epäonnistuu."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [VIRHE] {url}: {e}")
        return None


def save_json(data, path="data/data.json"):
    """Tallentaa datan JSON-tiedostoon."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Tallennettu: {path}")


def load_existing(path="data/data.json"):
    """Lataa olemassa olevan datan fallbackina."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ── Tiedonhaku: Katajan tulokset Flashscoresta ───────────────────────────────

def scrape_flashscore_kataja():
    """
    Yrittää hakea Katajan viimeisimmät tulokset Flashscoresta.
    Flashscore lataa datan JavaScriptillä, joten tavallinen haku
    palauttaa vain rungon — tämä toimii parhaiten otteluiden URL-listana.
    """
    print("Haetaan Flashscore / Kataja...")
    url = "https://www.flashscore.fi/joukkue/joensuun-kataja/xOGT6AD5/tulokset/"
    html = fetch(url)
    if not html:
        return None

    # Flashscore lataa tulokset JS:llä — etsitään mitä ikinä löytyy staattisesta HTML:stä
    results = []

    # Etsi ottelutietoja JSON-muotoisesta datasta sivun <script>-tageista
    # Flashscore käyttää sport-event formaattia
    pattern = re.compile(
        r'"homeTeam"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"[^}]*\}.*?'
        r'"awayTeam"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"[^}]*\}.*?'
        r'"homeScore"\s*:\s*(\d+).*?"awayScore"\s*:\s*(\d+)',
        re.DOTALL
    )
    for m in pattern.finditer(html):
        results.append({
            "home": m.group(1),
            "away": m.group(2),
            "home_score": int(m.group(3)),
            "away_score": int(m.group(4)),
        })

    print(f"  Flashscore: löydettiin {len(results)} ottelua")
    return results if results else None


# ── Tiedonhaku: sarjataulukko basket.fi:stä ──────────────────────────────────

def scrape_basket_fi_standings():
    """
    Yrittää hakea sarjataulukko-tiedot basket.fi:n tulospalvelusta.
    Sivusto käyttää TorneoPal-järjestelmää joka lataa datan dynaamisesti.
    """
    print("Haetaan sarjataulukko basket.fi:stä...")

    # Yritetään hakea JSON-dataa suoraan TorneoPal-API:sta
    # (basket.fi käyttää tätä taustalla)
    api_urls = [
        "https://tulospalvelu.basket.fi/api/category/4!huki2526/standings/",
        "https://tulospalvelu.basket.fi/category/4!huki2526/group/39344/",
    ]

    for url in api_urls:
        html = fetch(url)
        if not html:
            continue

        # Etsi joukkuetaulukko-dataa
        # TorneoPal palauttaa joskus JSON:ia suoraan
        try:
            data = json.loads(html)
            print(f"  Löydettiin JSON: {url}")
            return data
        except json.JSONDecodeError:
            pass

        # Etsi taulukkorivejä HTML:stä
        rows = re.findall(
            r'<tr[^>]*class="[^"]*standing[^"]*"[^>]*>(.*?)</tr>',
            html, re.DOTALL | re.IGNORECASE
        )
        if rows:
            print(f"  Löydettiin {len(rows)} riviä: {url}")
            standings = []
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                if len(cells) >= 4:
                    standings.append(cells)
            return standings

    print("  Sarjataulukko: ei löydetty automaattisesti")
    return None


# ── Tiedonhaku: Katajan seuraava ottelu ──────────────────────────────────────

def scrape_next_match():
    """Hakee Katajan seuraavan ottelun tiedot."""
    print("Haetaan seuraava ottelu...")
    url = "https://www.flashscore.fi/joukkue/joensuun-kataja/xOGT6AD5/"
    html = fetch(url)
    if not html:
        return None

    # Etsi päivämääräformaatteja tekstistä
    date_pattern = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{4})')
    dates = date_pattern.findall(html)
    if dates:
        print(f"  Löydettiin {len(dates)} päivämäärää")

    return None  # Flashscore vaatii JS:n — palautetaan None


# ── Koosta lopullinen data ───────────────────────────────────────────────────

def build_data():
    """Koostaa kaiken datan yhteen rakenteeseen."""

    # Staattinen pohja — päivitetään automaattisesti haetulla datalla
    # kun se on saatavilla, muuten käytetään näitä tietoja
    data = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "updated_fi": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "scrape_success": False,

        # Playoff-tilanne (päivitetään manuaalisesti tai automaattisesti)
        "playoff": {
            "semifinal_kataja": {
                "home": "Kataja Basket",
                "away": "Helsinki Seagulls",
                "series": "0-2",
                "kataja_leads": False,
                "status": "Käynnissä",
                "next_game": "21.4.2026 klo 18:30",
                "next_game_ts": "2026-04-21T18:30:00+03:00",
                "venue": "Motonet Areena, Joensuu"
            },
            "semifinal_other": {
                "home": "Salon Vilpas",
                "away": "UU-Korihait",
                "series": "1-1",
                "status": "Käynnissä"
            }
        },

        # Sarjataulukko — käytetään tunnettuja tietoja
        "standings": [
            {"pos": 1, "team": "Salon Vilpas",     "g": 32, "w": 25, "l": 7,  "pts": 57, "is_kataja": False, "in_playoffs": True},
            {"pos": 2, "team": "Kauhajoki",         "g": 32, "w": 21, "l": 11, "pts": 53, "is_kataja": False, "in_playoffs": True},
            {"pos": 3, "team": "Helsinki Seagulls", "g": 32, "w": 20, "l": 12, "pts": 52, "is_kataja": False, "in_playoffs": True},
            {"pos": 4, "team": "UU-Korihait",       "g": 32, "w": 19, "l": 13, "pts": 51, "is_kataja": False, "in_playoffs": True},
            {"pos": 5, "team": "Tapiolan Honka",    "g": 32, "w": 18, "l": 14, "pts": 50, "is_kataja": False, "in_playoffs": True},
            {"pos": 6, "team": "KTP-Basket",        "g": 32, "w": 17, "l": 15, "pts": 49, "is_kataja": False, "in_playoffs": True},
            {"pos": 7, "team": "Tampereen Pyrintö", "g": 32, "w": 15, "l": 17, "pts": 47, "is_kataja": False, "in_playoffs": True},
            {"pos": 8, "team": "Kataja Basket",     "g": 32, "w": 14, "l": 18, "pts": 46, "is_kataja": True,  "in_playoffs": True},
            {"pos": 9, "team": "Bisons Loimaa",     "g": 32, "w": 12, "l": 20, "pts": 44, "is_kataja": False, "in_playoffs": False},
            {"pos":10, "team": "Lahti Basketball",  "g": 32, "w": 11, "l": 21, "pts": 43, "is_kataja": False, "in_playoffs": False},
            {"pos":11, "team": "Kouvot",             "g": 32, "w": 9,  "l": 23, "pts": 41, "is_kataja": False, "in_playoffs": False},
            {"pos":12, "team": "Kobrat",             "g": 32, "w": 4,  "l": 28, "pts": 36, "is_kataja": False, "in_playoffs": False},
        ],

        # Viimeisimmät tulokset
        "results": [
            {"date": "18.4.2026", "home": "Helsinki Seagulls", "away": "Kataja Basket", "home_score": 85, "away_score": 80, "round": "Välierä 2", "kataja_win": False},
            {"date": "15.4.2026", "home": "Kataja Basket",     "away": "Helsinki Seagulls", "home_score": None, "away_score": None, "round": "Välierä 1", "kataja_win": False},
            {"date": "5.4.2026",  "home": "Kataja Basket",     "away": "Kauhajoki", "home_score": None, "away_score": None, "round": "Puolivälierä 4", "kataja_win": True},
            {"date": "2.4.2026",  "home": "Kauhajoki",         "away": "Kataja Basket", "home_score": None, "away_score": None, "round": "Puolivälierä 3", "kataja_win": True},
            {"date": "29.3.2026", "home": "Kataja Basket",     "away": "Kauhajoki", "home_score": None, "away_score": None, "round": "Puolivälierä 2", "kataja_win": True},
            {"date": "26.3.2026", "home": "Kauhajoki",         "away": "Kataja Basket", "home_score": None, "away_score": None, "round": "Puolivälierä 1", "kataja_win": True},
        ]
    }

    # Yritetään täydentää automaattisella datalla
    scraped_results = scrape_flashscore_kataja()
    if scraped_results:
        data["scrape_success"] = True
        data["scraped_results"] = scraped_results
        print(f"  Automaattinen haku onnistui: {len(scraped_results)} ottelua")
    else:
        print("  Automaattinen haku epäonnistui — käytetään staattisia tietoja")

    return data


# ── Pääohjelma ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print(f"Kataja Basket tiedonhaku — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("=" * 50)

    data = build_data()
    save_json(data)

    print("=" * 50)
    print(f"Valmis! Scrape success: {data['scrape_success']}")
    print(f"Päivitetty: {data['updated_fi']}")
