# Kataja Basket – verkkosivusto

Automaattisesti päivittyvä Kataja Basket -sivusto.  
Tiedot haetaan basket.fi:stä / Flashscoresta GitHub Actionsin kautta.

## Tiedostorakenne

```
kataja-basket/
├── index.html                     # Pääsivu
├── scrape.py                      # Python-skripti tiedonhakuun
├── data/
│   └── data.json                  # Automaattisesti päivitetty data
└── .github/
    └── workflows/
        └── update-data.yml        # GitHub Actions -ajastus
```

## Asennus (vaihe vaiheelta)

### 1. Luo GitHub-tili
Mene osoitteeseen https://github.com ja rekisteröidy ilmaiseksi.

### 2. Luo uusi repositorio
- Klikkaa vihreää **New**-nappia
- Repositorion nimi: `kataja-basket`
- Valitse **Public** (pakollinen GitHub Pages -toimintoa varten)
- Klikkaa **Create repository**

### 3. Lataa tiedostot GitHubiin
Ladattavat tiedostot (kaikki tästä paketista):
- `index.html`
- `scrape.py`
- `data/data.json`
- `.github/workflows/update-data.yml`

GitHubissa klikkaa **Add file → Upload files** ja lataa kaikki.

### 4. Ota GitHub Pages käyttöön
- Mene **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: **main**, kansio **/ (root)**
- Klikkaa **Save**

Sivusto on hetken kuluttua osoitteessa:
`https://KÄYTTÄJÄNIMI.github.io/kataja-basket`

### 5. Tarkista GitHub Actions
- Mene **Actions**-välilehdelle
- Skripti ajaa automaattisesti 5 min välein
- Voit ajaa sen myös manuaalisesti: **Run workflow**

## Päivittäminen

### Automaattinen päivitys
GitHub Actions ajaa `scrape.py`-skriptin joka 5. minuutti.
- Jos basket.fi/Flashscore sallii haun → tiedot päivittyvät automaattisesti
- Jos haku estetään → sivusto näyttää viimeisimmät tunnetut tiedot

### Manuaalinen päivitys
Muokkaa `data/data.json`-tiedostoa suoraan GitHubissa:
1. Klikkaa `data/data.json`
2. Klikkaa kynäikonia (Edit)
3. Muuta tiedot
4. Klikkaa **Commit changes**

Sivusto päivittyy automaattisesti muutamassa sekunnissa.

## Tietojen päivitys

Tärkeimmät kentät `data/data.json`:ssa:

```json
"playoff": {
  "semifinal_kataja": {
    "series": "0-2",           ← Muuta sarjatilannetta
    "next_game": "21.4.2026 klo 18:30",
    "next_game_ts": "2026-04-21T18:30:00+03:00"
  }
}
```

## Huomioita

- GitHub Actions saattaa viivästyä 5–30 min ruuhka-aikoina
- basket.fi ja Flashscore saattavat estää automaattisen haun
- Sivusto näyttää aina viimeisimmät tallennetut tiedot vaikka haku epäonnistuisi
- Tarkista ajantasaiset tiedot aina basket.fi:stä tai Flashscoresta
