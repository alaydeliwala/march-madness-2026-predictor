# March Madness 2026 - Pool-Winning Bracket Predictor

A data-driven bracket prediction system that analyzes 38 CSV files spanning 2008-2026 to produce a **pool-optimized** bracket. The key differentiator: instead of just picking the most likely winners, the system identifies **contrarian value** -- teams the data says are strong but the public is sleeping on.

<img width="1800" height="1188" alt="Screenshot 2026-03-19 at 10 30 51 AM" src="https://github.com/user-attachments/assets/e61a1e03-035f-4693-b7f0-22d11824d84f" />


## Quick Start

```bash
cd ~/Downloads/march-madness-data
pip3 install pandas numpy
python3 bracket_predictor.py
```

Output prints to stdout and is also saved to `bracket_output_2026.txt`.

## Project Files

| File | Description |
|------|-------------|
| `bracket_predictor.py` | Main prediction script (1,341 lines) |
| `bracket_output_2026.txt` | Full 67-game bracket with confidence scores |
| `parlays_2026.txt` | 6 data-driven parlay recommendations + futures |
| `bracket_predictor_architecture.excalidraw` | System architecture diagram (open in [excalidraw.com](https://excalidraw.com)) |
| `gen_excalidraw.py` | Generator script for the architecture diagram |
| `data/` | Subfolder containing all 38 CSV data sources (2008-2026) |

## How It Works

### 1. Data Ingestion

10 CSV files are loaded and merged on `TEAM NO + YEAR`:

| Source | Key Metrics | Purpose |
|--------|-------------|---------|
| KenPom Barttorvik | KADJ EM, KADJ D, BADJ EM, EXP, TOV% | Primary efficiency ratings |
| Barttorvik Neutral | BADJ EM (neutral court) | Tournament-relevant performance |
| EvanMiya | Relative Rating, Killshots, Injury Rank | Independent rating system |
| RPPF Ratings | RADJ EM | Third independent system |
| Shooting Splits | 3PT Share, 3PT%, defensive shooting | Shot volatility analysis |
| Resumes | NET, ELO, WAB, Q1 wins | Resume quality |
| Seed Results | Historical win rates by seed | Bayesian base rates |
| Coach Results | PASE (Performance Above Seed Expectation) | Coaching factor |
| Team Results | Program PASE, F4%, Championship% | Program history |
| Tournament Matchups | Bracket structure + historical results | Bracket tree + backtesting |

### 2. Composite Rating Engine

Each team gets a composite power rating built from z-score normalized metrics across two tiers:

**Tier 1 -- Core Efficiency (85% weight):**
- KADJ EM (KenPom adjusted efficiency margin): 25%
- BADJ EM (Barttorvik overall): 20%
- Neutral BADJ EM (neutral court only): 20%
- RADJ EM (RPPF adjusted): 10%
- Relative Rating (EvanMiya): 10%

**Tier 2 -- Adjustments (15% weight):**
- Defensive premium: 4% (lower KADJ D = better, tournament defense travels)
- Neutral court delta: 3% (penalize teams that drop on neutral courts)
- Experience: 2.5% (veterans handle March pressure)
- Turnover discipline: 2% (low-TO teams are consistent)
- 3PT stability: 1.5% (3PT-dependent teams are volatile)
- Coach PASE: 2% (tournament coaching track record)

### 3. Win Probability Model

**Logistic model** with three layers:

```
P(A wins) = 1 / (1 + 10^(-diff / sigma))
```

- `sigma = 3.40` (calibrated via backtesting 2012-2025)
- **Bayesian blend**: 85% model probability + 15% historical seed base rate
- **Round amplification**: Favorites get a small edge in later rounds (1.0x in R64 up to 1.12x in Championship)

### 4. Pool Value Optimizer

The system doesn't just pick favorites -- it maximizes **expected pool points** by identifying contrarian picks:

- **Upset budget**: R64 max 4, R32 max 2, S16 max 1, E8 max 1
- **Seed-specific thresholds**: 6v11 needs 44%+ model probability, 7v10 needs 46%+, etc.
- **Leverage score**: `P(win) x Points / Public Pick Rate` -- picks where the model sees value the public doesn't
- R64 upset candidates are ranked by leverage and the top N are selected

### 5. Historical Backtesting

The model is calibrated against 13 tournament years (2012-2025, excluding 2020):

| Metric | Result | Target |
|--------|--------|--------|
| Avg R64 accuracy | **73.7%** | 72-76% |
| Best year | 2017: 87.5% | -- |
| Worst year | 2024: 62.5% | -- |
| Sigma calibration | 3.40 | Optimized |

## 2026 Results

### Champion: Michigan (1-seed)

| Metric | Value |
|--------|-------|
| Composite rank | #1 overall (1.543) |
| KADJ EM | 37.59 |
| Defense (KADJ D) | 89.03 |
| Experience (EXP) | 1.95 (veteran) |
| Championship path probability | 6.06% |

### Final Four

| Region | Champion | Composite |
|--------|----------|-----------|
| East | (1) Duke | 1.404 |
| South | (2) Houston | 1.215 |
| West | (1) Arizona | 1.509 |
| Midwest | (1) Michigan | 1.543 |

### 5 Contrarian Upset Picks

| Pick | Round | Model % | Historical Context |
|------|-------|---------|-------------------|
| VCU (11) over UNC (6) | R64 | 48% | 6v11 upsets hit 50% historically |
| Texas A&M (10) over Saint Mary's (7) | R64 | 47% | 7v10 classic upset spot |
| NC State (11) over BYU (6) | R64 | 46% | ACC battle-tested 11-seed |
| Santa Clara (10) over Kentucky (7) | R64 | 48% | ELO rank 24 > Kentucky 45 |
| Tennessee (6) over Virginia (3) | R32 | 50% | Virginia worst PASE in field |

### Top 5 Composite Ratings

| Rank | Team | Seed | Composite | KADJ EM |
|------|------|------|-----------|---------|
| 1 | Michigan | 1 | 1.543 | 37.59 |
| 2 | Arizona | 1 | 1.509 | 37.66 |
| 3 | Duke | 1 | 1.404 | 38.90 |
| 4 | Purdue | 2 | 1.348 | 31.20 |
| 5 | Iowa St. | 2 | 1.302 | 32.42 |

## Key Analytical Insights

**Red Flags:**
- Duke (1): EXP 0.86, youngest team in the tournament
- Florida (1): Neutral BADJ EM drops 9.7 points from overall
- Alabama (4): 53.7% of shots from 3PT, most volatile offense
- Virginia (3): Worst combined coach + program PASE (-7.1 / -7.6)

**Dark Horses:**
- Vanderbilt (5): Plays like a 2-seed, EXP 2.31, KADJ EM 27.5
- Iowa (9): KADJ EM 22.4 > Clemson 19.2 -- the model favors the 9-seed
- Utah St. (9): ELO rank #14, model favors over Villanova

**Coaching Edges:**
- Tom Izzo (Michigan St.): #1 PASE out of 332 coaches
- John Calipari (Arkansas): #2 PASE
- Tony Bennett (Virginia): #331 PASE -- worst in the field

## Parlay Recommendations

See `parlays_2026.txt` for full details. Summary:

| Parlay | Legs | Model Prob | Est. Odds | Risk |
|--------|------|-----------|-----------|------|
| Chalk Crusher | 4 | 53.4% | +90-110 | Low |
| Model Edge | 3 | 14.2% | +600-700 | Medium |
| Upset Double | 2 | 22.8% | +350-425 | Medium |
| Dark Horse Path | 3 | 14.9% | +550-650 | Med-High |
| Long Shot Bomb | 4 | 5.1% | +1800-2200 | High |
| Houston Sweep | 3 | 30.8% | +225-275 | Med-Low |

Best expected value: **Model Edge** (Iowa/Utah St./VCU) and **Upset Double** (VCU/Santa Clara).

## Architecture

Open `bracket_predictor_architecture.excalidraw` in [excalidraw.com](https://excalidraw.com) for the full system diagram showing data flow, composite rating weights, win probability model, upset decision logic, and bracket simulation engine.

## Dependencies

- Python 3.10+
- pandas
- numpy

No ML libraries required -- the model uses logistic regression with Bayesian blending, implemented from scratch.
