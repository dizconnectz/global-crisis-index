# Global Crisis Index (GCI)

🌐 **Live site:** <https://dizconnectz.github.io/global-crisis-index/>

A 0–100 index of **systemic impact on the world**, built from four pillars: the economy & energy markets, geopolitical conflict, natural hazards at strategic hubs, and health & critical infrastructure.
The site is available in Thai and English, hosted free on **GitHub Pages**, and refreshed every 6 hours by **GitHub Actions** — no server, no database, no paid services.

| Score | Meaning |
|---|---|
| 0–20 | 🟢 Low systemic impact |
| 21–45 | 🟡 Watch / regional volatility |
| 46–70 | 🟠 High tension / global supply-chain impact |
| 71–100 | 🔴 Global systemic crisis |

---

## What the site shows

- **Headline score** with its level, a short plain-language summary, the top drivers, and a trend line of recent scores.
- **Early-warning watchlist** — up to three things worth watching over the next 1–3 months, each with its evidence. Kept separate from the score.
- **The four pillars** — each pillar's sub-score alongside the real numbers behind it (VIX, Brent crude, gold, event counts, and so on).
- **Local event notes** — serious events that hit one area only (for example, a strong earthquake far from global shipping routes). They are listed so readers stay informed, while their weight in the world score is deliberately limited.

## Design principles

- **Every number is computed by code, never by AI.** The site works fully without any AI key. AI (optional) only writes the summary text.
- **Missing data is never treated as zero.** If a source is down, the system uses its last valid value or leaves that pillar out — it never pretends the world got safer.
- **Weekends are normal.** Markets closed on Saturday/Sunday use Friday's close and are not flagged as an outage.
- **No double counting.** Fifty articles about the same story count as one event; what matters is how many independent outlets confirm it.
- **Local vs. global.** A disaster far from global supply-chain hubs is capped so it cannot inflate the world score.
- **Transparent status.** The header shows how fresh the data is and whether any source is delayed.

## Data sources (all free)

| Pillar | Sources |
|---|---|
| Economy, finance & energy | Yahoo Finance (via `yfinance`), FRED |
| Conflict & geopolitics | GDELT, BBC World, Al Jazeera, Reuters (via Google News) |
| Natural hazards | USGS earthquakes, GDACS alerts |
| Health & infrastructure | WHO Disease Outbreak News, CISA advisories (Google News fallback) |

---

## How the data updates

Everything runs in one GitHub Actions workflow: [`.github/workflows/update_and_deploy.yml`](.github/workflows/update_and_deploy.yml).

**Triggers**

| Trigger | When |
|---|---|
| Schedule (`17 */6 * * *`) | Every 6 hours at minute 17 UTC (00:17, 06:17, 12:17, 18:17 UTC). GitHub may start scheduled runs a few minutes late. |
| Manual | Actions tab → *Update index & deploy* → **Run workflow** |
| Code push to `main` | Rebuilds after code changes (data-only and README commits are ignored) |

**Each run**

1. `python scripts/update_index.py` — fetch all sources and compute the index
2. `pytest` — if any test fails, the run stops and nothing is published
3. The bot commits the refreshed JSON files back to the repository
4. `npm run build` — build the static site with the new data baked in
5. Deploy to GitHub Pages

**Where the data lives** — in this repository. Git is the database, so every update is a commit you can look back on.

| File | Contents | Public URL |
|---|---|---|
| `public/data/latest_state.json` | Current score, pillar scores, source status, watchlist, local notes (Thai + English) | [`/data/latest_state.json`](https://dizconnectz.github.io/global-crisis-index/data/latest_state.json) |
| `public/data/history.json` | Last 90 days of scores, for the trend chart | [`/data/history.json`](https://dizconnectz.github.io/global-crisis-index/data/history.json) |
| `data/state_cache.json` | Internal memory: ongoing events, last valid values, previous AI text | not published on the site |

> If you edit code locally, run `git pull` first — the bot commits new data every 6 hours.

---

## What happens when something goes wrong

The system is built so that **no single failure stops the site or produces a wrong score**. Scores never depend on AI, and missing data is never counted as zero.

### Gemini (AI summaries)

| Situation | What the system does | What visitors see | Action needed |
|---|---|---|---|
| **Free quota / tokens used up** (HTTP 429) | Catches the error and writes the summary from the built-in template in the same run. The next run tries Gemini again. | Same scores; summary reads more plainly; footer of the hero card says *Summary by rule-based template*. | None. If it happens every run, check usage at [Google AI Studio](https://aistudio.google.com/) or switch to a lighter model with the `GEMINI_MODEL` variable. |
| Nothing new since the last run | Skips the AI call (0 tokens) and reuses the previous AI text. This keeps usage far below the free quota. | *Summary by Gemini (previous run)*. | None. |
| API key missing, wrong or revoked | Runs in template mode. | Template summary. | Add or replace the `GEMINI_API_KEY` secret. |
| Gemini overloaded (HTTP 503 "high demand") | Retries once after a few seconds, then uses the template. The next run tries again. | Template summary for that run. | None. |
| Gemini slow or unreachable | Gives up after 60 seconds and uses the template. | Template summary. | None. |
| Gemini returns broken or incomplete JSON | Rejects the response and uses the template. | Template summary. | None. |
| Gemini quotes the score or invents local notes | Code removes them: a summary containing a score is replaced by the template's; local notes are cleared when there are no local events. | Clean summary. | None. |
| The prompt is changed in code | Cached AI text from the old prompt is discarded and regenerated. | New-style summary on the next run. | None. |

### Data sources

| Situation | What the system does | What visitors see | Action needed |
|---|---|---|---|
| One source fails (e.g. a news feed) | Scores the pillar from the remaining sources. | Header: *Some data delayed*; pillar marked the same. | None, unless it persists for days. |
| GDELT rate-limits us (common on shared GitHub servers) | Treated as a supplementary source; the other news feeds carry the pillar. | Header stays *Normal*. | None. |
| cisa.gov blocks GitHub's servers | Automatically uses Google News results from cisa.gov instead. | Normal. | None. |
| Every source for a pillar fails | Uses that pillar's last valid score if it is under 72 hours old; otherwise leaves the pillar out of the average and re-weights the rest. **Never substitutes 0.** | Pillar marked *Using last valid value* or *Data missing*. | Check the run log if it lasts more than a day. |
| All sources fail at once | Each pillar falls back to its last valid score (up to 72 h old). Only if none is left is the headline score shown as "—" instead of a made-up number. | *Some data delayed*, or "—" with an explanation. | Check the Actions log. |
| Weekend / market holiday | Uses the last close (Friday) as a normal value. | *Market closed (weekend)*. | None. |
| A source changes its format | That source fails (see above); the rest keep working. | *Some data delayed*. | Update the matching fetcher in `scripts/gci/fetchers/`. |

### Pipeline, GitHub and the website

| Situation | What the system does | What visitors see | Action needed |
|---|---|---|---|
| A test fails during a run | Stops before committing or deploying. | The previous version of the site stays online; the freshness badge turns *Delayed* after 7 h and *Stale data* after 13 h. | Open the failed run in the Actions tab and fix the cause. |
| A scheduled run starts late or is skipped | The next run catches up. | Freshness badge reflects the real data age. | None. |
| Two runs overlap | They queue one after the other (never in parallel). | Nothing. | None. |
| You push code while the bot pushes data | The bot rebases on your commit before pushing. | Nothing. | Run `git pull` before editing locally. |
| GitHub Pages deploy fails | The last successful deploy stays online. | Previous version. | Re-run the workflow. |
| Scheduled runs stop after long inactivity | GitHub may pause schedules on inactive repositories; the bot's regular data commits normally prevent this. | Freshness badge turns *Stale data*. | Actions tab → re-enable the workflow. |
| Someone forks the repository | The fork has no access to your secrets and runs in template mode. | — | None. |
| Visitor still sees an old version | GitHub Pages lets browsers cache pages for up to 10 minutes. | Old page. | Hard refresh (Ctrl+Shift+R). |

---

## Project layout

```
config/scoring_rules.json      All tunable settings (weights, thresholds, keywords, strategic hubs)
scripts/update_index.py        Pipeline entry point
scripts/gci/fetchers/          Data fetchers: markets, news, hazards, health/cyber
scripts/gci/scoring.py         Scoring, news de-duplication, event decay, local/global filter
scripts/gci/validators.py      Missing-data rules and source/pillar status
scripts/gci/ai_helper.py       Optional Gemini summaries + rule-based fallback (Thai & English)
scripts/gci/pipeline.py        Assembles everything into the JSON files
tests/test_scoring.py          Unit tests
app/, components/, lib/        Next.js + Tailwind website (static export)
```

## Deploy your own copy

1. Fork or push this repository to GitHub (branch `main`).
2. **Settings → Pages → Build and deployment → Source:** choose **GitHub Actions**.
3. **Settings → Actions → General → Workflow permissions:** choose **Read and write permissions**.
4. *(Optional)* For more natural summaries, add a Gemini API key:
   - Get a free key at <https://aistudio.google.com/apikey>
   - **Settings → Secrets and variables → Actions → New repository secret**, name it `GEMINI_API_KEY`
   - *(Optional)* add a repository variable `GEMINI_MODEL` (default: `gemini-2.5-flash`)
   - Without a key the site still works, using built-in templates.
5. Run it once: **Actions → Update index & deploy → Run workflow**.
   Your site will be at `https://<user>.github.io/<repo>/`.

## Run locally

```bash
pip install -r requirements.txt
python -m pytest -q tests                  # run the tests
python scripts/update_index.py             # fetch live data, write public/data/*.json
python scripts/update_index.py --dry-run   # compute only, write nothing

npm install
npm run dev                                # http://localhost:3000
npm run build                              # static export to out/
```

To use Gemini locally, set the `GEMINI_API_KEY` environment variable (and optionally `GEMINI_MODEL`) before running `update_index.py`.

## Tuning

All settings live in `config/scoring_rules.json`: pillar weights, market reference points, news keywords and severity levels, event decay, strategic hubs and their radius, and the caps for local events. After changing anything, run `pytest` to confirm the safety properties (caps, missing-data handling, de-duplication) still hold.

## Limitations

- News is classified using English keywords, so some events may be missed or put in the wrong category.
- Headlines are shown in their original language (English).
- The index measures systemic impact on the world, not the human toll in any one place.
- It updates every 6 hours. It is not a real-time warning system and not investment advice.
- The watchlist summarises reported news. It is not a probability forecast.
- GDELT limits request rates. When it is unavailable, the conflict pillar relies on the remaining news feeds.

## License & attribution

- **Source code** — [MIT License](LICENSE). You may use, modify and redistribute it, keeping the copyright and license notice.
- **Index data and site content** (`public/data/`, GCI scores, text on the website) — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). You may use or cite them, but **you must give credit**:

> Source: Global Crisis Index (GCI) by dizconnectz — https://dizconnectz.github.io/global-crisis-index/

Third-party source data (Yahoo Finance, FRED, GDELT, BBC, Al Jazeera, Reuters, USGS, GDACS, WHO, CISA) belongs to its respective owners and remains subject to their terms.
