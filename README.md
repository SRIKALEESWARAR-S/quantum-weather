# Cosmic Circuit Daily

A static science dashboard that refreshes online every day using GitHub Actions. It combines astronomy, quantum research, weather and a genuine PennyLane circuit simulation.

## Features

- **Astronomy:** NASA Astronomy Picture of the Day (APOD) plus recent astrophysics papers from arXiv.
- **Quantum research:** recent arXiv `quant-ph` papers.
- **PennyLane lab:** each daily refresh runs a two-qubit circuit on PennyLane's `default.qubit` simulator and stores basis-state probabilities, a Pauli-Z expectation, shot count, angle and circuit drawing. This is a classical simulation, not physical quantum hardware.
- **Weather:** current conditions and a three-day forecast from Open-Meteo.
- **Daily pipeline:** GitHub Actions runs daily at 06:50 India Standard Time and can also be started manually.
- **Static front end:** no server required; suitable for GitHub Pages.

## Deploy to an existing GitHub repository

1. Download and extract the ZIP.
2. Upload the **contents** of this folder to the root of your repository. Keep `index.html`, `data.json`, `update.py`, `requirements.txt`, `config.json`, `test_update.py`, and `.github/workflows/daily-refresh.yml` in those exact locations.
3. Commit the files to the branch your GitHub Pages site publishes from.
4. In GitHub, open **Settings → Actions → General** and ensure workflows have permission to read and write repository contents. The workflow also needs `contents: write` permission.
5. Open **Actions → Refresh Cosmic Circuit Daily → Run workflow**. The first run installs PennyLane, tests the helpers, collects data, runs the circuit, and commits updated `data.json`.
6. When the run succeeds, reload your website. GitHub Pages may take a short time to publish the change.

## Weather location

The starter `config.json` uses Coimbatore, India. Change the city, country, latitude, longitude and timezone in `config.json` to your preferred location before committing. The optional GitHub Actions repository variables `WEATHER_CITY`, `WEATHER_LATITUDE` and `WEATHER_LONGITUDE` override the config file values.

## NASA API key

The NASA APOD source defaults to the shared `DEMO_KEY`, which is rate-limited. For more reliable use, create a personal key at <https://api.nasa.gov/> and add it in GitHub under **Settings → Secrets and variables → Actions → New repository secret**, named `NASA_API_KEY`. The workflow will use it automatically. A NASA key is optional; arXiv and weather still run if APOD fails.

## Data sources and caveats

- NASA APOD: <https://api.nasa.gov/>
- arXiv Atom API: <https://info.arxiv.org/help/api/index.html>
- Open-Meteo: <https://open-meteo.com/en/docs>
- PennyLane: <https://pennylane.ai/>

The collector uses official/public APIs instead of scraping search-result pages. Source outages are recorded in `data.json` and the last successful article data is preserved where possible. Weather data is a forecast/provider product, not an official emergency alert. Cite original sources when reusing papers or images.

## Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python update.py
```

Open `index.html` using a local static server rather than `file://`, because browsers commonly block `fetch('./data.json')` on local file URLs. For example:

```bash
python -m http.server 8000
```

Then open <http://localhost:8000>.

## Troubleshooting

- **Workflow missing:** verify `.github/workflows/daily-refresh.yml` is committed to the repository root.
- **Push rejected:** enable workflow write permissions under Settings → Actions → General.
- **PennyLane step fails:** check the dependency install log and Python version; the pipeline intentionally does not fabricate quantum results if PennyLane fails.
- **Some sources fail:** inspect the workflow logs and the `errors` array in `data.json`. Public services can rate-limit requests temporarily.
- **Website still looks old:** confirm GitHub Pages publishes from the branch/folder containing the new `index.html`, then wait for deployment.
