#!/usr/bin/env python3
"""
Kataja Basket - tiedonhakuskripti
Hakee tiedot API-Sports basketball API:sta (api-basketball.com)
API-avain luetaan ympäristömuuttujasta BASKETBALL_API_KEY
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

API_KEY   = os.environ.get("BASKETBALL_API_KEY", "")
API_BASE  = "https://v1.basketball.api-sports.io"
DATA_FILE = "data/data.json"
SEASON    = "2025-2026"

def api_get(endpoint, params=None):
    if not API_KEY:
        print("  [VIRHE] BASKETBALL_API_KEY puuttuu!")
        return None
    url = f"{API_BASE}/{endpoint}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    headers = {"x-apisports-key": API_KEY, "Accept": "application/json"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("errors") and data["errors"]:
                print(f"  [API VIRHE] {data['errors']}")
                return None
            remaining = resp.headers.get("x-ratelimit-requests-remaining", "?")
            print(f"  [OK] /{endpoint} — pyyntöjä jäljellä: {remaining}")
            return data
    except urllib.error.HTTPError as e:
        print(f"  [HTTP {e.code}] {e.reason}")
        return None
    except Exception as e:
        print(f"  [VIRHE] {e}")
        return None

def get_league_id():
    print("Haetaan Korisliigan ID...")
    data = api_get("leagues", {"name": "Korisliiga", "season": SEASON})
    if data and data.get("response"):
        for l in data["response"]:
            if "Korisliiga" in l.get("name","") and l.get("country",{}).get("name","") == "Finland":
                print(f"  Löytyi: ID={l['id']}")
                return l["id"]
    print("  Käytetään oletusarvoa 119")
    return 119  # Korisliigan tunnettu ID

def get_team_id(league_id):
    print("Haetaan Katajan ID...")
    data = api_get("teams", {"league": league_id, "season": SEASON})
    if data and data.get("response"):
        for t in data["response"]:
            if "Kataja" in t.get("name",""):
                print(f"  Löytyi: ID={t['id']}, nimi={t['name']}")
                return t["id"]
    print("  Ei löydy")
    return None

def get_standings(league_id):
    print("Haetaan sarjataulukko...")
    data = api_get("standings", {"league": league_id, "season": SEASON})
    if not data or not data.get("response"):
        return None
    rows = []
    for group in data["response"]:
        for e in group:
            name = e.get("team",{}).get("name","")
            rows.append({
                "pos":        e.get("position", 0),
                "team":       name,
                "g":          e.get("games",{}).get("played",{}).get("all", 0),
                "w":          e.get("games",{}).get("win",{}).get("all", 0),
                "l":          e.get("games",{}).get("lose",{}).get("all", 0),
                "pts":        e.get("points",{}).get("for", 0),
                "is_kataja":  "Kataja" in name,
                "in_playoffs": e.get("position", 99) <= 8,
            })
    rows.sort(key=lambda x: x["pos"])
    print(f"  {len(rows)} joukkuetta")
    return rows or None

def get_results(league_id, team_id):
    print("Haetaan viimeisimmät ottelut...")
    data = api_get("games", {"league": league_id, "season": SEASON, "team": team_id, "last": 10})
    if not data or not data.get("response"):
        return None
    results = []
    for g in reversed(data["response"]):
        home = g.get("teams",{}).get("home",{}).get("name","")
        away = g.get("teams",{}).get("away",{}).get("name","")
        hs   = g.get("scores",{}).get("home",{}).get("total")
        as_  = g.get("scores",{}).get("away",{}).get("total")
        kh   = "Kataja" in home
        kw   = None
        if hs is not None and as_ is not None:
            kw = (kh and hs > as_) or (not kh and as_ > hs)
        try:
            dt = datetime.fromisoformat(g.get("date","").replace("Z","+00:00"))
            df = dt.strftime("%d.%m.%Y")
        except Exception:
            df = g.get("date","")[:10]
        results.append({"date": df, "home": home, "away": away,
                        "home_score": hs, "away_score": as_,
                        "round": g.get("league",{}).get("round",""),
                        "kataja_win": kw,
                        "status": g.get("status",{}).get("long","")})
    print(f"  {len(results)} ottelua")
    return results or None

def get_next_game(league_id, team_id):
    print("Haetaan seuraava ottelu...")
    data = api_get("games", {"league": league_id, "season": SEASON, "team": team_id, "next": 1})
    if not data or not data.get("response"):
        return None
    for g in data["response"]:
        home = g.get("teams",{}).get("home",{}).get("name","")
        away = g.get("teams",{}).get("away",{}).get("name","")
        ds   = g.get("date","")
        try:
            dt = datetime.fromisoformat(ds.replace("Z","+00:00"))
            df = dt.strftime("%d.%m.%Y klo %H:%M")
            ts = dt.isoformat()
        except Exception:
            df, ts = ds, ds
        venue = g.get("venue","") or "Motonet Areena, Joensuu"
        print(f"  Seuraava: {home} – {away}, {df}")
        return {"home": home, "away": away, "next_game": df,
                "next_game_ts": ts, "venue": venue,
                "round": g.get("league",{}).get("round","")}
    return None

def load_existing():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Tallennettu: {DATA_FILE}")

def main():
    print("=" * 55)
    print(f"Kataja Basket päivitys — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("=" * 55)

    existing = load_existing()
    data = {
        "updated":        datetime.now(timezone.utc).isoformat(),
        "updated_fi":     datetime.now().strftime("%d.%m.%Y %H:%M"),
        "scrape_success": False,
    }

    if not API_KEY:
        print("VIRHE: BASKETBALL_API_KEY puuttuu ympäristömuuttujista!")
        if existing:
            existing["updated_fi"] = data["updated_fi"]
            save(existing)
        return

    league_id = get_league_id()
    team_id   = get_team_id(league_id)

    if not team_id:
        print("Katajan ID:tä ei löydy — käytetään olemassa olevaa dataa")
        if existing:
            existing["updated_fi"] = data["updated_fi"]
            save(existing)
        return

    standings = get_standings(league_id)
    results   = get_results(league_id, team_id)
    next_game = get_next_game(league_id, team_id)

    data["scrape_success"] = bool(standings or results or next_game)
    data["standings"]      = standings or (existing or {}).get("standings", [])
    data["results"]        = results   or (existing or {}).get("results", [])

    playoff = (existing or {}).get("playoff", {})
    if next_game:
        sf = playoff.get("semifinal_kataja", {})
        sf.update(next_game)
        playoff["semifinal_kataja"] = sf
    data["playoff"] = playoff

    save(data)

    print("=" * 55)
    print(f"{'✅ Onnistui' if data['scrape_success'] else '⚠️  Osittain'} — {data['updated_fi']}")

if __name__ == "__main__":
    main()
