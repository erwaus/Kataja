#!/usr/bin/env python3
"""
Kataja Basket - tiedonhakuskripti
Käyttää Highlightly Basketball API:a (basketball.highlightly.net)
API-avain luetaan ympäristömuuttujasta HIGHLIGHTLY_API_KEY
Ilmainen taso: 100 pyyntöä/päivä
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

API_KEY   = os.environ.get("HIGHLIGHTLY_API_KEY", "")
API_BASE  = "https://basketball.highlightly.net"
DATA_FILE = "data/data.json"

# ── API-apufunktio ────────────────────────────────────────────────────────────

def api_get(endpoint, params=None):
    if not API_KEY:
        print("  [VIRHE] HIGHLIGHTLY_API_KEY puuttuu!")
        return None
    url = f"{API_BASE}/{endpoint}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    headers = {"x-rapidapi-key": API_KEY, "Accept": "application/json"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            remaining = resp.headers.get("x-ratelimit-requests-remaining", "?")
            print(f"  [OK] /{endpoint} — pyyntöjä jäljellä: {remaining}")
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [HTTP {e.code}] {e.reason}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  [VIRHE] {e}")
        return None

# ── Etsi Korisliigan league ID ────────────────────────────────────────────────

def get_league_id():
    print("Haetaan Korisliigan ID...")
    data = api_get("leagues", {"countryCode": "FI"})
    if not data:
        return None
    leagues = data if isinstance(data, list) else data.get("leagues", [])
    for l in leagues:
        name = l.get("name", "")
        if "Korisliiga" in name or "korisliiga" in name.lower():
            lid = l.get("id")
            print(f"  Löytyi: ID={lid}, nimi={name}")
            return lid
    # Kokeile nimellä
    data2 = api_get("leagues", {"name": "Korisliiga"})
    if data2:
        leagues2 = data2 if isinstance(data2, list) else data2.get("leagues", [])
        for l in leagues2:
            if "Korisliiga" in l.get("name", ""):
                lid = l.get("id")
                print(f"  Löytyi nimellä: ID={lid}")
                return lid
    print("  Korisliigaa ei löydy")
    return None

# ── Etsi Katajan team ID ──────────────────────────────────────────────────────

def get_team_id(league_id):
    print("Haetaan Katajan team ID...")
    data = api_get("teams", {"leagueId": league_id})
    if not data:
        return None
    teams = data if isinstance(data, list) else data.get("teams", [])
    for t in teams:
        name = t.get("name", "")
        if "Kataja" in name or "kataja" in name.lower():
            tid = t.get("id")
            print(f"  Löytyi: ID={tid}, nimi={name}")
            return tid
    print("  Katajaa ei löydy")
    return None

# ── Hae sarjataulukko ─────────────────────────────────────────────────────────

def get_standings(league_id):
    print("Haetaan sarjataulukko...")
    data = api_get("standings", {"leagueId": league_id})
    if not data:
        return None
    standings_raw = data if isinstance(data, list) else data.get("standings", [])
    rows = []
    for i, e in enumerate(standings_raw):
        team = e.get("team", {}) if isinstance(e.get("team"), dict) else {}
        name = team.get("name", "") or e.get("teamName", "") or e.get("name", "")
        rows.append({
            "pos":        e.get("position", i + 1),
            "team":       name,
            "g":          e.get("gamesPlayed", e.get("played", 0)),
            "w":          e.get("wins", e.get("won", 0)),
            "l":          e.get("losses", e.get("lost", 0)),
            "pts":        e.get("points", 0),
            "is_kataja":  "Kataja" in name,
            "in_playoffs": e.get("position", i + 1) <= 8,
        })
    rows.sort(key=lambda x: x["pos"])
    print(f"  {len(rows)} joukkuetta")
    return rows or None

# ── Hae viimeisimmät ottelut ──────────────────────────────────────────────────

def get_results(team_id):
    print("Haetaan viimeisimmät ottelut...")
    data = api_get("last-five-games", {"teamId": team_id})
    if not data:
        return None
    games = data if isinstance(data, list) else data.get("games", data.get("matches", []))
    results = []
    for g in games:
        home_t = g.get("homeTeam", {}) if isinstance(g.get("homeTeam"), dict) else {}
        away_t = g.get("awayTeam", {}) if isinstance(g.get("awayTeam"), dict) else {}
        home = home_t.get("name", "") or g.get("homeTeamName", "")
        away = away_t.get("name", "") or g.get("awayTeamName", "")
        hs   = g.get("homeScore", g.get("homeGoals"))
        as_  = g.get("awayScore", g.get("awayGoals"))
        kh   = "Kataja" in home
        kw   = None
        if hs is not None and as_ is not None:
            try:
                kw = (kh and int(hs) > int(as_)) or (not kh and int(as_) > int(hs))
            except Exception:
                pass
        ds = g.get("date", g.get("startTime", ""))
        try:
            dt = datetime.fromisoformat(str(ds).replace("Z", "+00:00"))
            df = dt.strftime("%d.%m.%Y")
        except Exception:
            df = str(ds)[:10]
        results.append({
            "date": df, "home": home, "away": away,
            "home_score": hs, "away_score": as_,
            "round": g.get("round", g.get("league", {}).get("round", "")),
            "kataja_win": kw,
            "status": g.get("status", "")
        })
    print(f"  {len(results)} ottelua")
    return results or None

# ── Hae seuraava ottelu ───────────────────────────────────────────────────────

def get_next_game(league_id, team_id):
    print("Haetaan seuraava ottelu...")
    today = datetime.now().strftime("%Y-%m-%d")
    data  = api_get("matches", {"leagueId": league_id, "date": today})
    if not data:
        return None
    matches = data if isinstance(data, list) else data.get("matches", [])
    for g in matches:
        home_t = g.get("homeTeam", {}) if isinstance(g.get("homeTeam"), dict) else {}
        away_t = g.get("awayTeam", {}) if isinstance(g.get("awayTeam"), dict) else {}
        home = home_t.get("name", "") or g.get("homeTeamName", "")
        away = away_t.get("name", "") or g.get("awayTeamName", "")
        if "Kataja" in home or "Kataja" in away:
            ds = g.get("date", g.get("startTime", ""))
            try:
                dt = datetime.fromisoformat(str(ds).replace("Z", "+00:00"))
                df = dt.strftime("%d.%m.%Y klo %H:%M")
                ts = dt.isoformat()
            except Exception:
                df, ts = str(ds), str(ds)
            venue = g.get("venue", "") or ("Motonet Areena, Joensuu" if "Kataja" in home else "")
            print(f"  Seuraava: {home} – {away}, {df}")
            return {"home": home, "away": away,
                    "next_game": df, "next_game_ts": ts,
                    "venue": venue,
                    "round": g.get("round", "")}
    print("  Ei tulevia otteluita tänään")
    return None

# ── Apufunktiot ───────────────────────────────────────────────────────────────

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

# ── Pääohjelma ────────────────────────────────────────────────────────────────

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
        print("VIRHE: HIGHLIGHTLY_API_KEY puuttuu!")
        print("Lisää se GitHubin Settings → Secrets → Actions")
        if existing:
            existing["updated_fi"] = data["updated_fi"]
            save(existing)
        return

    league_id = get_league_id()
    team_id   = get_team_id(league_id) if league_id else None

    if not league_id or not team_id:
        print("Leaguen tai joukkueen ID:tä ei löydy")
        if existing:
            existing["updated_fi"] = data["updated_fi"]
            save(existing)
        return

    standings = get_standings(league_id)
    results   = get_results(team_id)
    next_game = get_next_game(league_id, team_id)

    data["scrape_success"] = bool(standings or results)
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
