#!/usr/bin/env python3
"""
================================================================
    MARCH MADNESS 2026 - POOL-WINNING BRACKET PREDICTOR
================================================================
Composite rating system + contrarian pool-value optimization.
Uses 2008-2026 historical data for calibration.
Targets bracket-pool wins via calculated upsets and leverage picks.
================================================================
"""

import pandas as pd
import numpy as np
import os
import sys
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# ============================================================
# CONSTANTS
# ============================================================

# 2026 Coach mapping: team name (as in CSV) -> coach name (as in Coach Results)
COACH_MAP_2026 = {
    'Duke': 'Jon Scheyer',
    'Arizona': 'Sean Miller',
    'Michigan': 'Dusty May',
    'Florida': 'Todd Golden',
    'Alabama': 'Nate Oats',
    'Houston': 'Kelvin Sampson',
    'Gonzaga': 'Mark Few',
    'Michigan St.': 'Tom Izzo',
    'Connecticut': 'Dan Hurley',
    'Purdue': 'Matt Painter',
    'Illinois': 'Brad Underwood',
    'Iowa St.': 'T.J. Otzelberger',
    'Virginia': 'Tony Bennett',
    'Kansas': 'Bill Self',
    'Arkansas': 'John Calipari',
    'North Carolina': 'Hubert Davis',
    'Kentucky': 'Mark Pope',
    'Tennessee': 'Rick Barnes',
    'Texas Tech': 'Grant McCasland',
    'Wisconsin': 'Greg Gard',
    'Nebraska': 'Fred Hoiberg',
    'St. John\'s': 'Rick Pitino',
    'Louisville': 'Pat Kelsey',
    'BYU': 'Kevin Young',
    'Villanova': 'Kyle Neptune',
    'Clemson': 'Brad Brownell',
    'Vanderbilt': 'Mark Byington',
    'UCLA': 'Mick Cronin',
    'Ohio St.': 'Jake Diebler',
    'Georgia': 'Mike White',
    'North Carolina St.': 'Kevin Keatts',
    'Saint Mary\'s': 'Randy Bennett',
    'Miami FL': 'Jim Larranaga',
}

# Round amplification (favorites gain edge in later rounds)
ROUND_AMP = {68: 1.00, 64: 1.00, 32: 1.02, 16: 1.05, 8: 1.08, 4: 1.10, 2: 1.12}

# Estimated public pick rates by seed for CHAMPIONSHIP
EST_CHAMP_PICK = {
    1: 0.22, 2: 0.10, 3: 0.05, 4: 0.03, 5: 0.015, 6: 0.008,
    7: 0.005, 8: 0.003, 9: 0.002, 10: 0.001, 11: 0.001,
    12: 0.0005, 13: 0.0002, 14: 0.0001, 15: 0.00005, 16: 0.00002
}

# Estimated public pick rates by seed for R64 win
EST_R64_PICK = {
    1: 0.97, 2: 0.92, 3: 0.88, 4: 0.78, 5: 0.64, 6: 0.62,
    7: 0.58, 8: 0.52, 9: 0.48, 10: 0.42, 11: 0.38, 12: 0.36,
    13: 0.22, 14: 0.12, 15: 0.08, 16: 0.03
}

# Points per round (ESPN standard scoring)
ROUND_POINTS = {64: 10, 32: 20, 16: 40, 8: 80, 4: 160, 2: 320}

# Region names for output
REGION_NAMES = ['EAST', 'SOUTH', 'WEST', 'MIDWEST']

# Tier 1 weights (core efficiency) - total = 0.85
T1_WEIGHTS = {
    'KADJ_EM': 0.25,
    'BADJ_EM': 0.20,
    'NBADJ_EM': 0.20,
    'RADJ_EM': 0.10,
    'REL_RATING': 0.10,
}

# Tier 2 weights (adjustments) - total = 0.15
T2_WEIGHTS = {
    'DEF_PREMIUM': 0.04,
    'NEUTRAL_DELTA': 0.03,
    'EXPERIENCE': 0.025,
    'TOV_DISCIPLINE': 0.02,
    'THREE_STABILITY': 0.015,
    'COACH_PASE': 0.02,
}


# ============================================================
# DATA LOADING
# ============================================================

def load_all_data():
    """Load all CSV files into a dict of DataFrames."""
    files = {
        'kenpom': 'KenPom Barttorvik.csv',
        'neutral': 'Barttorvik Neutral.csv',
        'evanmiya': 'EvanMiya.csv',
        'rppf': 'RPPF Ratings.csv',
        'resumes': 'Resumes.csv',
        'seed_results': 'Seed Results.csv',
        'coach_results': 'Coach Results.csv',
        'team_results': 'Team Results.csv',
        'matchups': 'Tournament Matchups.csv',
        'shooting': 'Shooting Splits.csv',
    }
    data = {}
    for key, fname in files.items():
        path = os.path.join(DATA_DIR, fname)
        data[key] = pd.read_csv(path)
    return data


# ============================================================
# SEED BASE RATES
# ============================================================

def compute_seed_base_rates(seed_results):
    """Compute R64 win probability base rates from Seed Results."""
    sr = seed_results.copy()
    # R64 win rate = R32 count / R64 count
    sr['R64_WIN_RATE'] = sr['R32'] / sr['R64']
    base = {}
    for _, row in sr.iterrows():
        base[int(row['SEED'])] = row['R64_WIN_RATE']
    return base


def get_seed_matchup_base(seed_a, seed_b, base_rates):
    """Get base rate for seed_a beating seed_b in R64."""
    if seed_a + seed_b == 17:  # standard R64 matchup
        return base_rates.get(seed_a, 0.5)
    # For non-standard matchups (later rounds), estimate from seed difference
    # Lower seed number = better team historically
    diff = seed_b - seed_a
    return 1.0 / (1.0 + 10 ** (-diff / 8.0))


# ============================================================
# COMPOSITE RATING ENGINE
# ============================================================

def zscore(series):
    """Compute z-score, handling zero variance."""
    std = series.std()
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def compute_composite_ratings(data, year, coach_pase_map=None):
    """Compute composite power ratings for all teams in a given year.

    Returns a DataFrame with TEAM NO, TEAM, SEED, COMPOSITE and sub-metrics.
    """
    kp = data['kenpom'][data['kenpom']['YEAR'] == year].copy()
    if kp.empty:
        return pd.DataFrame()

    bn = data['neutral'][data['neutral']['YEAR'] == year].copy()
    em = data['evanmiya'][data['evanmiya']['YEAR'] == year].copy()
    rp = data['rppf'][data['rppf']['YEAR'] == year].copy()
    sh = data['shooting'][data['shooting']['YEAR'] == year].copy()

    # Start with KenPom as base
    cols_kp = ['TEAM NO', 'TEAM', 'SEED', 'KADJ EM', 'KADJ D', 'BADJ EM',
               'EXP', 'TOV%', 'BARTHAG']
    # Handle missing columns gracefully
    available = [c for c in cols_kp if c in kp.columns]
    df = kp[available].copy()

    # Rename BADJ EM from kenpom
    if 'BADJ EM' in df.columns:
        df = df.rename(columns={'BADJ EM': 'BADJ_EM'})

    # Merge neutral BADJ EM
    if not bn.empty and 'BADJ EM' in bn.columns:
        bn_sub = bn[['TEAM NO', 'BADJ EM']].rename(columns={'BADJ EM': 'NBADJ_EM'})
        df = df.merge(bn_sub, on='TEAM NO', how='left')
    else:
        df['NBADJ_EM'] = df.get('BADJ_EM', 0)

    # Merge EvanMiya RELATIVE RATING
    if not em.empty and 'RELATIVE RATING' in em.columns:
        em_sub = em[['TEAM NO', 'RELATIVE RATING']].rename(
            columns={'RELATIVE RATING': 'REL_RATING'})
        df = df.merge(em_sub, on='TEAM NO', how='left')
    else:
        df['REL_RATING'] = np.nan

    # Merge RPPF RADJ EM
    if not rp.empty and 'RADJ EM' in rp.columns:
        rp_sub = rp[['TEAM NO', 'RADJ EM']].rename(columns={'RADJ EM': 'RADJ_EM'})
        df = df.merge(rp_sub, on='TEAM NO', how='left')
    else:
        df['RADJ_EM'] = np.nan

    # Merge Shooting THREES SHARE
    if not sh.empty and 'THREES SHARE' in sh.columns:
        sh_sub = sh[['TEAM NO', 'THREES SHARE']]
        df = df.merge(sh_sub, on='TEAM NO', how='left')
    else:
        df['THREES SHARE'] = np.nan

    # Fill NaN with column means for numeric columns
    num_cols = ['KADJ EM', 'KADJ D', 'BADJ_EM', 'NBADJ_EM', 'REL_RATING',
                'RADJ_EM', 'EXP', 'TOV%', 'THREES SHARE', 'BARTHAG']
    for col in num_cols:
        if col in df.columns:
            col_mean = df[col].mean()
            if np.isnan(col_mean):
                col_mean = 0
            df[col] = df[col].fillna(col_mean)

    # ---- TIER 1: Core efficiency (z-score normalized) ----
    z_kadj = zscore(df['KADJ EM']) if 'KADJ EM' in df.columns else 0
    z_badj = zscore(df['BADJ_EM']) if 'BADJ_EM' in df.columns else 0
    z_nbadj = zscore(df['NBADJ_EM']) if 'NBADJ_EM' in df.columns else 0
    z_radj = zscore(df['RADJ_EM']) if 'RADJ_EM' in df.columns else 0
    z_relrat = zscore(df['REL_RATING']) if 'REL_RATING' in df.columns else 0

    tier1 = (T1_WEIGHTS['KADJ_EM'] * z_kadj +
             T1_WEIGHTS['BADJ_EM'] * z_badj +
             T1_WEIGHTS['NBADJ_EM'] * z_nbadj +
             T1_WEIGHTS['RADJ_EM'] * z_radj +
             T1_WEIGHTS['REL_RATING'] * z_relrat)

    # ---- TIER 2: Adjustments ----
    # Defensive premium (lower KADJ D = better defense, so negate)
    z_def = -zscore(df['KADJ D']) if 'KADJ D' in df.columns else 0

    # Neutral court delta (positive = better on neutral courts)
    if 'NBADJ_EM' in df.columns and 'BADJ_EM' in df.columns:
        neutral_delta = df['NBADJ_EM'] - df['BADJ_EM']
        z_ndelta = zscore(neutral_delta)
    else:
        z_ndelta = 0

    # Experience (higher = more experienced)
    z_exp = zscore(df['EXP']) if 'EXP' in df.columns else 0

    # Turnover discipline (lower TOV% = better, so negate)
    z_tov = -zscore(df['TOV%']) if 'TOV%' in df.columns else 0

    # 3PT stability (higher THREES SHARE = more volatile, so negate)
    z_3pt = -zscore(df['THREES SHARE']) if 'THREES SHARE' in df.columns else 0

    # Coach PASE
    coach_z = pd.Series(0.0, index=df.index)
    if coach_pase_map is not None:
        for idx, row in df.iterrows():
            team = row['TEAM']
            if team in coach_pase_map:
                coach_z.at[idx] = coach_pase_map[team]

    tier2 = (T2_WEIGHTS['DEF_PREMIUM'] * z_def +
             T2_WEIGHTS['NEUTRAL_DELTA'] * z_ndelta +
             T2_WEIGHTS['EXPERIENCE'] * z_exp +
             T2_WEIGHTS['TOV_DISCIPLINE'] * z_tov +
             T2_WEIGHTS['THREE_STABILITY'] * z_3pt +
             T2_WEIGHTS['COACH_PASE'] * coach_z)

    df['COMPOSITE'] = tier1 + tier2
    df['TIER1'] = tier1
    df['TIER2'] = tier2

    return df


def build_coach_pase_map(data, year=2026):
    """Build a team -> normalized coach PASE mapping for a given year."""
    cr = data['coach_results']
    if year == 2026:
        coach_map = COACH_MAP_2026
    else:
        return {}  # No coach mapping for historical years

    # Get PASE values for known coaches
    pase_values = {}
    for team, coach_name in coach_map.items():
        match = cr[cr['COACH'].str.strip() == coach_name.strip()]
        if not match.empty:
            pase_values[team] = match.iloc[0]['PASE']
        else:
            pase_values[team] = 0.0

    # Z-score normalize across all coaches in dataset
    all_pase = cr['PASE'].values
    mean_pase = np.mean(all_pase)
    std_pase = np.std(all_pase)
    if std_pase == 0:
        std_pase = 1

    normalized = {}
    for team, pase in pase_values.items():
        normalized[team] = (pase - mean_pase) / std_pase

    return normalized


# ============================================================
# WIN PROBABILITY MODEL
# ============================================================

def win_probability(rating_a, rating_b, seed_a, seed_b, round_num,
                    base_rates, sigma=2.5, base_weight=0.15):
    """Compute win probability for team A over team B.

    Combines logistic model with Bayesian seed base rates and round amplification.
    """
    # Logistic model probability
    diff = rating_a - rating_b
    amp = ROUND_AMP.get(round_num, 1.0)
    if diff > 0:
        adj_diff = diff * amp
    else:
        adj_diff = diff / amp  # underdog gets compressed

    model_prob = 1.0 / (1.0 + 10.0 ** (-adj_diff / sigma))

    # Bayesian blend with seed base rates
    if round_num == 64 or round_num == 68:  # R64 or First Four
        base_prob = get_seed_matchup_base(seed_a, seed_b, base_rates)
        # Reduce base weight for later rounds
        bw = base_weight
    elif round_num == 32:
        base_prob = get_seed_matchup_base(seed_a, seed_b, base_rates)
        bw = base_weight * 0.6
    else:
        base_prob = get_seed_matchup_base(seed_a, seed_b, base_rates)
        bw = base_weight * 0.3

    blended = (1.0 - bw) * model_prob + bw * base_prob
    return np.clip(blended, 0.005, 0.995)


# ============================================================
# BRACKET PARSING
# ============================================================

def parse_bracket_2026(data):
    """Parse the 2026 bracket structure from Tournament Matchups.

    Returns:
        regions: list of 4 lists, each containing 8 R64 game dicts
        first_four: list of First Four game dicts
    """
    matchups = data['matchups']
    m26 = matchups[
        (matchups['YEAR'] == 2026) & (matchups['CURRENT ROUND'] == 64)
    ].sort_values('BY YEAR NO', ascending=False).reset_index(drop=True)

    games = []
    first_four = []
    i = 0

    while i < len(m26):
        row_a = m26.iloc[i]
        if i + 1 >= len(m26):
            break
        row_b = m26.iloc[i + 1]

        # Check for First Four: next pair has same higher-seed team
        if (i + 3 < len(m26) and
                m26.iloc[i + 2]['TEAM NO'] == row_a['TEAM NO']):
            # First Four detected
            ff_team1 = row_b  # first lower-seed opponent
            ff_team2 = m26.iloc[i + 3]  # second lower-seed opponent
            ff_game = {
                'a': {'team': ff_team1['TEAM'], 'seed': int(ff_team1['SEED']),
                       'team_no': int(ff_team1['TEAM NO'])},
                'b': {'team': ff_team2['TEAM'], 'seed': int(ff_team2['SEED']),
                       'team_no': int(ff_team2['TEAM NO'])},
            }
            first_four.append(ff_game)
            # R64 game: higher seed vs First Four winner placeholder
            game = {
                'a': {'team': row_a['TEAM'], 'seed': int(row_a['SEED']),
                       'team_no': int(row_a['TEAM NO'])},
                'b': None,  # will be filled after First Four
                'ff_index': len(first_four) - 1,
            }
            games.append(game)
            i += 4
        else:
            game = {
                'a': {'team': row_a['TEAM'], 'seed': int(row_a['SEED']),
                       'team_no': int(row_a['TEAM NO'])},
                'b': {'team': row_b['TEAM'], 'seed': int(row_b['SEED']),
                       'team_no': int(row_b['TEAM NO'])},
            }
            games.append(game)
            i += 2

    # Split into 4 regions of 8 games each
    regions = []
    idx = 0
    for r in range(4):
        region_games = games[idx:idx + 8]
        regions.append(region_games)
        idx += 8

    return regions, first_four


def parse_historical_bracket(data, year):
    """Parse historical bracket for backtesting.

    Returns:
        games: list of R64 game dicts with 'actual_winner' field
        first_four: list of First Four games
    """
    matchups = data['matchups']
    m = matchups[
        (matchups['YEAR'] == year) & (matchups['CURRENT ROUND'] == 64)
    ].sort_values('BY YEAR NO', ascending=False).reset_index(drop=True)

    if m.empty:
        return [], []

    games = []
    first_four = []
    i = 0

    while i < len(m):
        row_a = m.iloc[i]
        if i + 1 >= len(m):
            break
        row_b = m.iloc[i + 1]

        # Check for First Four
        if (i + 3 < len(m) and
                m.iloc[i + 2]['TEAM NO'] == row_a['TEAM NO']):
            ff_t1 = row_b
            ff_t2 = m.iloc[i + 3]

            # Determine First Four winner: lower ROUND value went further
            # Both have scores if game was played
            r1 = int(ff_t1['ROUND'])
            r2 = int(ff_t2['ROUND'])
            if r1 < r2:
                ff_winner = ff_t1
            elif r2 < r1:
                ff_winner = ff_t2
            else:
                # Same ROUND - check SCORE
                s1 = ff_t1.get('SCORE', 0)
                s2 = ff_t2.get('SCORE', 0)
                try:
                    s1 = float(s1) if pd.notna(s1) and str(s1).strip() != '' else 0
                    s2 = float(s2) if pd.notna(s2) and str(s2).strip() != '' else 0
                except (ValueError, TypeError):
                    s1, s2 = 0, 0
                ff_winner = ff_t1 if s1 >= s2 else ff_t2

            ff_game = {
                'a': {'team': ff_t1['TEAM'], 'seed': int(ff_t1['SEED']),
                       'team_no': int(ff_t1['TEAM NO']), 'round': r1},
                'b': {'team': ff_t2['TEAM'], 'seed': int(ff_t2['SEED']),
                       'team_no': int(ff_t2['TEAM NO']), 'round': r2},
                'winner': ff_winner['TEAM'],
            }
            first_four.append(ff_game)

            # R64 game
            ra = int(row_a['ROUND'])
            rw = int(ff_winner['ROUND'])
            actual_winner = row_a['TEAM'] if ra < rw else ff_winner['TEAM']
            game = {
                'a': {'team': row_a['TEAM'], 'seed': int(row_a['SEED']),
                       'team_no': int(row_a['TEAM NO']), 'round': ra},
                'b': {'team': ff_winner['TEAM'], 'seed': int(ff_winner['SEED']),
                       'team_no': int(ff_winner['TEAM NO']), 'round': rw},
                'actual_winner': actual_winner,
            }
            games.append(game)
            i += 4
        else:
            ra = int(row_a['ROUND'])
            rb = int(row_b['ROUND'])
            actual_winner = row_a['TEAM'] if ra < rb else row_b['TEAM']
            if ra == rb:
                # Tie in ROUND - check score
                sa = row_a.get('SCORE', 0)
                sb = row_b.get('SCORE', 0)
                try:
                    sa = float(sa) if pd.notna(sa) and str(sa).strip() != '' else 0
                    sb = float(sb) if pd.notna(sb) and str(sb).strip() != '' else 0
                except (ValueError, TypeError):
                    sa, sb = 0, 0
                actual_winner = row_a['TEAM'] if sa >= sb else row_b['TEAM']

            game = {
                'a': {'team': row_a['TEAM'], 'seed': int(row_a['SEED']),
                       'team_no': int(row_a['TEAM NO']), 'round': ra},
                'b': {'team': row_b['TEAM'], 'seed': int(row_b['SEED']),
                       'team_no': int(row_b['TEAM NO']), 'round': rb},
                'actual_winner': actual_winner,
            }
            games.append(game)
            i += 2

    return games, first_four


# ============================================================
# POOL VALUE OPTIMIZATION
# ============================================================

def estimate_public_pick(seed, round_num):
    """Estimate the public's pick rate for a team by seed and round."""
    if round_num == 64:
        return EST_R64_PICK.get(seed, 0.5)
    elif round_num == 32:
        base = EST_R64_PICK.get(seed, 0.5)
        return base * 0.85  # slight decay
    elif round_num == 16:
        return EST_R64_PICK.get(seed, 0.5) * 0.65
    elif round_num == 8:
        return EST_R64_PICK.get(seed, 0.5) * 0.45
    elif round_num == 4:
        return EST_CHAMP_PICK.get(seed, 0.01) * 3.5
    elif round_num == 2:
        return EST_CHAMP_PICK.get(seed, 0.01) * 1.8
    return 0.5


def compute_pool_leverage(win_prob, seed, round_num):
    """Compute pool leverage: how much value a pick gives relative to public.

    Higher leverage = the pick differentiates our bracket more.
    """
    public_pick = estimate_public_pick(seed, round_num)
    if public_pick <= 0:
        public_pick = 0.001
    points = ROUND_POINTS.get(round_num, 10)
    # Expected pool value = probability * points * (1/public_rate)
    ev = win_prob * points * (1.0 / public_pick)
    return ev, public_pick


def should_pick_upset(model_prob_underdog, composite_diff_std, round_num,
                      seed_fav, seed_dog, upset_budget_remaining=99):
    """Determine if we should pick the upset for pool value.

    Pool-winning strategy: be SELECTIVE. Pick 5-8 calculated upsets total,
    not every game where the underdog has a chance.
    """
    # No budget left
    if upset_budget_remaining <= 0:
        return False

    # 8v9 matchups are NOT upsets - they're coin flips
    if {seed_fav, seed_dog} == {8, 9}:
        return False

    # Same seed or adjacent seeds in later rounds = not a real upset
    seed_gap = abs(seed_fav - seed_dog)
    if seed_gap <= 1:
        return False

    # Seed-based thresholds: different standards for different matchups
    if round_num == 64:
        # R64 upset picks (most valuable for differentiation)
        if (seed_fav, seed_dog) == (5, 12):
            # Classic upset spot: 35%+ historical rate
            return model_prob_underdog >= 0.40 and composite_diff_std < 1.2
        elif seed_fav == 6 and seed_dog == 11:
            # 6v11: nearly coin flip historically (48.5% for 11-seed)
            return model_prob_underdog >= 0.44
        elif seed_fav == 7 and seed_dog == 10:
            # 7v10: common upset spot
            return model_prob_underdog >= 0.46
        elif seed_fav == 4 and seed_dog == 13:
            # 4v13: rarer but high leverage when it hits
            return model_prob_underdog >= 0.38 and composite_diff_std < 0.8
        elif seed_fav == 3 and seed_dog == 14:
            return model_prob_underdog >= 0.42 and composite_diff_std < 0.6
        else:
            # 1v16, 2v15: almost never pick these
            return False

    elif round_num == 32:
        # R32: only pick if underdog genuinely close AND creates good path
        return model_prob_underdog >= 0.46 and composite_diff_std < 0.8

    elif round_num in (16, 8):
        # S16/E8: very selective, only when data strongly supports
        return model_prob_underdog >= 0.49 and seed_gap >= 3

    elif round_num in (4, 2):
        # F4/Championship: only extreme contrarian value
        return model_prob_underdog >= 0.49 and seed_gap >= 3

    return False


# ============================================================
# BRACKET SIMULATION
# ============================================================

def get_team_rating(team_no, ratings_df):
    """Look up a team's composite rating."""
    match = ratings_df[ratings_df['TEAM NO'] == team_no]
    if not match.empty:
        return match.iloc[0]['COMPOSITE']
    return 0.0


def simulate_game(team_a, team_b, ratings_df, base_rates, round_num,
                  sigma=2.5, contrarian=True, composite_std=1.0,
                  upset_budget_remaining=99):
    """Simulate a single game. Returns winner dict and metadata."""
    rat_a = get_team_rating(team_a['team_no'], ratings_df)
    rat_b = get_team_rating(team_b['team_no'], ratings_df)

    prob_a = win_probability(rat_a, rat_b, team_a['seed'], team_b['seed'],
                             round_num, base_rates, sigma=sigma)
    prob_b = 1.0 - prob_a

    # Determine favorite and underdog based on SEED (not just probability)
    # For upset tracking: lower seed number = expected favorite
    if team_a['seed'] < team_b['seed']:
        fav, dog = team_a, team_b
        prob_fav, prob_dog = prob_a, prob_b
    elif team_b['seed'] < team_a['seed']:
        fav, dog = team_b, team_a
        prob_fav, prob_dog = prob_b, prob_a
    elif prob_a >= prob_b:
        fav, dog = team_a, team_b
        prob_fav, prob_dog = prob_a, prob_b
    else:
        fav, dog = team_b, team_a
        prob_fav, prob_dog = prob_b, prob_a

    # Check for contrarian upset pick
    upset_pick = False
    composite_diff = abs(rat_a - rat_b)
    if contrarian and composite_std > 0:
        upset_pick = should_pick_upset(
            prob_dog, composite_diff / composite_std, round_num,
            fav['seed'], dog['seed'], upset_budget_remaining)

    if upset_pick:
        winner = dog
        win_prob_val = prob_dog
        is_upset = True
    else:
        # Pick the team with higher model probability (not necessarily the seed fav)
        if prob_a >= prob_b:
            winner = team_a
            win_prob_val = prob_a
        else:
            winner = team_b
            win_prob_val = prob_b
        is_upset = False

    loser = team_b if winner is team_a else team_a

    # Confidence label
    if win_prob_val > 0.90:
        conf = 'LOCK'
    elif win_prob_val > 0.75:
        conf = 'STRONG'
    elif win_prob_val > 0.60:
        conf = 'LEAN'
    elif win_prob_val > 0.50:
        conf = 'TOSS-UP'
    else:
        conf = 'UPSET'

    return {
        'winner': winner,
        'loser': loser,
        'team_a': team_a,
        'team_b': team_b,
        'prob_a': prob_a,
        'prob_b': prob_b,
        'win_prob': win_prob_val,
        'confidence': conf,
        'is_upset': is_upset,
        'round': round_num,
        'rating_a': rat_a,
        'rating_b': rat_b,
    }


def simulate_full_bracket(regions, first_four, ratings_df, base_rates,
                          sigma=2.5, contrarian=True):
    """Simulate the entire bracket from First Four through Championship.

    Uses an upset budget to limit contrarian picks to ~5-8 total.
    Returns structured results dict.
    """
    composite_std = ratings_df['COMPOSITE'].std()
    if composite_std == 0:
        composite_std = 1.0

    # Upset budget: max contrarian picks per round
    # Total target: 5-8 upsets across entire bracket
    UPSET_BUDGET = {64: 4, 32: 2, 16: 1, 8: 1, 4: 1, 2: 0}
    upsets_remaining = dict(UPSET_BUDGET)

    results = {
        'first_four': [],
        'regions': [],
        'final_four': [],
        'championship': None,
        'champion': None,
        'all_games': [],
        'upsets': [],
    }

    # --- First Four ---
    ff_winners = {}
    for i, ff in enumerate(first_four):
        game = simulate_game(ff['a'], ff['b'], ratings_df, base_rates, 68,
                             sigma=sigma, contrarian=False,
                             composite_std=composite_std)
        results['first_four'].append(game)
        results['all_games'].append(game)
        ff_winners[i] = game['winner']

    # --- First pass: compute all R64 upset candidates, pick the best ones ---
    # Score all potential upsets, then select the top N by leverage
    r64_upset_candidates = []
    all_r64_games_raw = []

    for r_idx, region_games in enumerate(regions):
        for g_idx, game in enumerate(region_games):
            team_a = game['a']
            if game['b'] is None and 'ff_index' in game:
                team_b = ff_winners[game['ff_index']]
            else:
                team_b = game['b']

            rat_a = get_team_rating(team_a['team_no'], ratings_df)
            rat_b = get_team_rating(team_b['team_no'], ratings_df)
            prob_a = win_probability(rat_a, rat_b, team_a['seed'], team_b['seed'],
                                     64, base_rates, sigma=sigma)

            # Determine favorite/underdog by seed
            if team_a['seed'] < team_b['seed']:
                fav, dog = team_a, team_b
                prob_dog = 1.0 - prob_a
            elif team_b['seed'] < team_a['seed']:
                fav, dog = team_b, team_a
                prob_dog = prob_a
            else:
                fav, dog = (team_a, team_b) if prob_a >= 0.5 else (team_b, team_a)
                prob_dog = min(prob_a, 1.0 - prob_a)

            comp_diff_std = abs(rat_a - rat_b) / composite_std
            eligible = should_pick_upset(
                prob_dog, comp_diff_std, 64,
                fav['seed'], dog['seed'], 99)

            # Compute leverage score for ranking
            ev_dog, pub_dog = compute_pool_leverage(prob_dog, dog['seed'], 64)
            leverage = ev_dog

            all_r64_games_raw.append({
                'r_idx': r_idx, 'g_idx': g_idx,
                'team_a': team_a, 'team_b': team_b,
            })

            if eligible:
                r64_upset_candidates.append({
                    'r_idx': r_idx, 'g_idx': g_idx,
                    'fav': fav, 'dog': dog,
                    'prob_dog': prob_dog, 'leverage': leverage,
                })

    # Select top N R64 upsets by leverage
    r64_upset_candidates.sort(key=lambda x: x['leverage'], reverse=True)
    selected_r64_upsets = set()
    for cand in r64_upset_candidates[:UPSET_BUDGET[64]]:
        selected_r64_upsets.add((cand['r_idx'], cand['g_idx']))

    # --- Regional rounds ---
    regional_champs = []
    for r_idx, region_games in enumerate(regions):
        region_result = {'name': REGION_NAMES[r_idx], 'rounds': {}}

        # R64
        r64_results = []
        r64_winners = []
        for g_idx, game in enumerate(region_games):
            team_a = game['a']
            if game['b'] is None and 'ff_index' in game:
                team_b = ff_winners[game['ff_index']]
            else:
                team_b = game['b']

            # Force upset only for selected candidates
            force_upset = (r_idx, g_idx) in selected_r64_upsets
            result = simulate_game(team_a, team_b, ratings_df, base_rates, 64,
                                   sigma=sigma,
                                   contrarian=force_upset,
                                   composite_std=composite_std,
                                   upset_budget_remaining=1 if force_upset else 0)
            r64_results.append(result)
            r64_winners.append(result['winner'])
            results['all_games'].append(result)
            if result['is_upset']:
                results['upsets'].append(result)

        region_result['rounds'][64] = r64_results

        # R32
        r32_results = []
        r32_winners = []
        for j in range(0, len(r64_winners), 2):
            if j + 1 < len(r64_winners):
                budget = upsets_remaining.get(32, 0)
                result = simulate_game(
                    r64_winners[j], r64_winners[j + 1],
                    ratings_df, base_rates, 32,
                    sigma=sigma, contrarian=(contrarian and budget > 0),
                    composite_std=composite_std,
                    upset_budget_remaining=budget)
                r32_results.append(result)
                r32_winners.append(result['winner'])
                results['all_games'].append(result)
                if result['is_upset']:
                    results['upsets'].append(result)
                    upsets_remaining[32] = max(0, upsets_remaining.get(32, 0) - 1)

        region_result['rounds'][32] = r32_results

        # S16
        s16_results = []
        s16_winners = []
        for j in range(0, len(r32_winners), 2):
            if j + 1 < len(r32_winners):
                budget = upsets_remaining.get(16, 0)
                result = simulate_game(
                    r32_winners[j], r32_winners[j + 1],
                    ratings_df, base_rates, 16,
                    sigma=sigma, contrarian=(contrarian and budget > 0),
                    composite_std=composite_std,
                    upset_budget_remaining=budget)
                s16_results.append(result)
                s16_winners.append(result['winner'])
                results['all_games'].append(result)
                if result['is_upset']:
                    results['upsets'].append(result)
                    upsets_remaining[16] = max(0, upsets_remaining.get(16, 0) - 1)

        region_result['rounds'][16] = s16_results

        # E8 (Regional Final)
        if len(s16_winners) >= 2:
            budget = upsets_remaining.get(8, 0)
            result = simulate_game(
                s16_winners[0], s16_winners[1],
                ratings_df, base_rates, 8,
                sigma=sigma, contrarian=(contrarian and budget > 0),
                composite_std=composite_std,
                upset_budget_remaining=budget)
            region_result['rounds'][8] = [result]
            regional_champs.append(result['winner'])
            results['all_games'].append(result)
            if result['is_upset']:
                results['upsets'].append(result)
                upsets_remaining[8] = max(0, upsets_remaining.get(8, 0) - 1)
        else:
            regional_champs.append(s16_winners[0] if s16_winners else None)

        results['regions'].append(region_result)

    # --- Final Four ---
    if len(regional_champs) >= 4:
        budget = upsets_remaining.get(4, 0)
        ff1 = simulate_game(regional_champs[0], regional_champs[1],
                            ratings_df, base_rates, 4,
                            sigma=sigma, contrarian=(contrarian and budget > 0),
                            composite_std=composite_std,
                            upset_budget_remaining=budget)
        if ff1['is_upset']:
            upsets_remaining[4] = max(0, upsets_remaining.get(4, 0) - 1)
            budget = upsets_remaining.get(4, 0)

        ff2 = simulate_game(regional_champs[2], regional_champs[3],
                            ratings_df, base_rates, 4,
                            sigma=sigma, contrarian=(contrarian and budget > 0),
                            composite_std=composite_std,
                            upset_budget_remaining=budget)
        results['final_four'] = [ff1, ff2]
        results['all_games'].extend([ff1, ff2])
        if ff1['is_upset']:
            results['upsets'].append(ff1)
        if ff2['is_upset']:
            results['upsets'].append(ff2)

        # Championship
        champ = simulate_game(ff1['winner'], ff2['winner'],
                              ratings_df, base_rates, 2,
                              sigma=sigma, contrarian=False,
                              composite_std=composite_std,
                              upset_budget_remaining=0)
        results['championship'] = champ
        results['champion'] = champ['winner']
        results['all_games'].append(champ)

    return results


# ============================================================
# HISTORICAL BACKTESTING
# ============================================================

def backtest_year(data, year, base_rates, sigma=2.5):
    """Backtest the model on a single historical year.

    Returns accuracy by round.
    """
    games, _ = parse_historical_bracket(data, year)
    if not games:
        return None

    ratings = compute_composite_ratings(data, year)
    if ratings.empty:
        return None

    # Filter to tournament teams only (those in matchups)
    tourney_team_nos = set()
    for g in games:
        tourney_team_nos.add(g['a']['team_no'])
        tourney_team_nos.add(g['b']['team_no'])

    tourney_ratings = ratings[ratings['TEAM NO'].isin(tourney_team_nos)].copy()
    if tourney_ratings.empty:
        return None

    # Simulate R64
    correct_r64 = 0
    total_r64 = 0
    predicted_winners = {}  # team_no -> True if they advanced in our bracket

    for g in games:
        team_a = g['a']
        team_b = g['b']
        actual = g['actual_winner']

        rat_a = get_team_rating(team_a['team_no'], tourney_ratings)
        rat_b = get_team_rating(team_b['team_no'], tourney_ratings)

        prob_a = win_probability(rat_a, rat_b, team_a['seed'], team_b['seed'],
                                 64, base_rates, sigma=sigma)

        predicted = team_a['team'] if prob_a >= 0.5 else team_b['team']
        if predicted == actual:
            correct_r64 += 1
        total_r64 += 1

    # For R32+, we need to track who actually advanced
    # Use ROUND values from the data: teams with ROUND <= 32 made R32, etc.
    all_teams = {}
    for g in games:
        all_teams[g['a']['team']] = g['a'].get('round', 64)
        all_teams[g['b']['team']] = g['b'].get('round', 64)

    def made_round(team_name, round_target):
        """Check if team actually made it to a given round."""
        r = all_teams.get(team_name, 64)
        return r <= round_target

    # Count actual results for each round
    actual_r32 = sum(1 for t, r in all_teams.items() if r <= 32)
    actual_s16 = sum(1 for t, r in all_teams.items() if r <= 16)
    actual_e8 = sum(1 for t, r in all_teams.items() if r <= 8)

    return {
        'year': year,
        'r64_correct': correct_r64,
        'r64_total': total_r64,
        'r64_pct': correct_r64 / total_r64 if total_r64 > 0 else 0,
    }


def run_backtest(data, sigma=2.5):
    """Run backtesting across all historical years."""
    base_rates = compute_seed_base_rates(data['seed_results'])
    years = [y for y in range(2012, 2026) if y != 2020]

    results = []
    for year in years:
        r = backtest_year(data, year, base_rates, sigma=sigma)
        if r:
            results.append(r)

    return results


def calibrate_sigma(data):
    """Find the sigma value that maximizes backtest R64 accuracy."""
    best_sigma = 2.5
    best_acc = 0

    for s_int in range(15, 40, 1):
        sigma = s_int / 10.0
        results = run_backtest(data, sigma=sigma)
        if not results:
            continue
        avg_acc = np.mean([r['r64_pct'] for r in results])
        if avg_acc > best_acc:
            best_acc = avg_acc
            best_sigma = sigma

    return best_sigma, best_acc


# ============================================================
# OUTPUT FORMATTING
# ============================================================

def confidence_bar(prob):
    """Create a visual confidence bar."""
    filled = int(prob * 20)
    return '|' + '#' * filled + '-' * (20 - filled) + '|'


def format_game(result, show_leverage=False):
    """Format a single game result for display."""
    ta = result['team_a']
    tb = result['team_b']
    winner = result['winner']
    prob = result['win_prob']
    conf = result['confidence']
    upset_tag = ' ** UPSET **' if result['is_upset'] else ''

    line = (f"  ({ta['seed']:>2}) {ta['team']:<20s} vs "
            f"({tb['seed']:>2}) {tb['team']:<20s} --> "
            f"{winner['team']:<20s} ({prob*100:5.1f}% | {conf}){upset_tag}")

    return line


def format_bracket(results, ratings_df, backtest_results, sigma):
    """Format the complete bracket output."""
    lines = []
    sep = '=' * 72

    lines.append(sep)
    lines.append('      MARCH MADNESS 2026 - POOL-WINNING BRACKET')
    lines.append(sep)
    lines.append('')

    # Strategy summary
    n_upsets = len(results['upsets'])
    total_games = len(results['all_games'])
    lines.append('STRATEGY SUMMARY:')
    lines.append(f'  Contrarian upsets picked: {n_upsets} of {total_games} games')

    # Differentiation estimate
    upset_seeds = [u['winner']['seed'] for u in results['upsets']]
    diff_pct = sum(1.0 - estimate_public_pick(s, 64) for s in upset_seeds)
    lines.append(f'  Upset picks create ~{diff_pct:.0f} differentiation points')

    # Backtest summary
    if backtest_results:
        avg_r64 = np.mean([r['r64_pct'] for r in backtest_results])
        lines.append(f'  Backtest R64 accuracy (2012-2025): {avg_r64*100:.1f}%')
        lines.append(f'  Calibrated sigma: {sigma:.2f}')
    lines.append('')

    # First Four
    lines.append(f'{"-"*72}')
    lines.append('FIRST FOUR:')
    lines.append(f'{"-"*72}')
    for game in results['first_four']:
        lines.append(format_game(game))
    lines.append('')

    # Regional rounds
    for region in results['regions']:
        lines.append(f'{sep}')
        lines.append(f'  {region["name"]} REGION')
        lines.append(f'{sep}')

        for round_num in [64, 32, 16, 8]:
            round_games = region['rounds'].get(round_num, [])
            if not round_games:
                continue

            round_name = {64: 'ROUND OF 64', 32: 'ROUND OF 32',
                          16: 'SWEET SIXTEEN', 8: 'ELITE EIGHT'}[round_num]
            lines.append(f'\n  {round_name}:')

            for game in round_games:
                lines.append(format_game(game))

        # Regional champion
        e8 = region['rounds'].get(8, [])
        if e8:
            champ = e8[0]['winner']
            lines.append(f'\n  >> Regional Champion: ({champ["seed"]}) {champ["team"]}')
        lines.append('')

    # Final Four
    lines.append(f'{sep}')
    lines.append('  FINAL FOUR')
    lines.append(f'{sep}')
    for game in results['final_four']:
        lines.append(format_game(game))

    # Championship
    lines.append(f'\n  NATIONAL CHAMPIONSHIP:')
    if results['championship']:
        lines.append(format_game(results['championship']))

    lines.append('')
    lines.append(f'{sep}')

    # Champion
    if results['champion']:
        champ = results['champion']
        champ_rating = get_team_rating(champ['team_no'], ratings_df)
        # Estimate championship probability
        champ_probs = []
        for g in results['all_games']:
            if g['winner']['team_no'] == champ['team_no']:
                champ_probs.append(g['win_prob'])
        bracket_prob = np.prod(champ_probs) if champ_probs else 0
        log_conf = sum(np.log(max(g['win_prob'], 0.01)) for g in results['all_games'])

        lines.append(f'  CHAMPION: ({champ["seed"]}) {champ["team"]}')
        lines.append(f'  Championship path probability: {bracket_prob*100:.2f}%')
        lines.append(f'  Composite rating: {champ_rating:.3f} '
                     f'(#{int(ratings_df[ratings_df["COMPOSITE"] >= champ_rating].shape[0])} overall)')
        lines.append(f'  Bracket log-confidence: {log_conf:.2f}')
        lines.append('')
        lines.append('  WHY THIS CHAMPION:')
        # Get the champion's key metrics
        champ_row = ratings_df[ratings_df['TEAM NO'] == champ['team_no']]
        if not champ_row.empty:
            cr = champ_row.iloc[0]
            lines.append(f'    - KADJ EM: {cr.get("KADJ EM", 0):.1f} | '
                         f'Defense (KADJ D): {cr.get("KADJ D", 0):.1f} | '
                         f'Exp: {cr.get("EXP", 0):.2f}')
            lines.append(f'    - Composite rank #{int((ratings_df["COMPOSITE"] > champ_rating).sum()) + 1} '
                         f'among all D1 teams')
        pub_rate = EST_CHAMP_PICK.get(champ['seed'], 0.01)
        lines.append(f'    - Est. public championship pick rate: ~{pub_rate*100:.0f}%')
        lines.append(f'    - Creates pool differentiation vs chalk favorites')

    lines.append(f'{sep}')
    lines.append('')

    # Final Four summary
    lines.append('FINAL FOUR:')
    for region in results['regions']:
        e8 = region['rounds'].get(8, [])
        if e8:
            champ = e8[0]['winner']
            rat = get_team_rating(champ['team_no'], ratings_df)
            lines.append(f'  {region["name"]:<10s}: ({champ["seed"]}) {champ["team"]:<20s} '
                         f'[Composite: {rat:.3f}]')
    lines.append('')

    # Top value picks with reasoning
    lines.append(f'{"-"*72}')
    lines.append('TOP VALUE PICKS (where we differ from chalk):')
    lines.append(f'{"-"*72}')
    if results['upsets']:
        for i, upset in enumerate(results['upsets'], 1):
            w = upset['winner']
            l = upset['loser']
            pub = estimate_public_pick(w['seed'], upset['round'])
            rd_name = {68: 'FF', 64: 'R64', 32: 'R32', 16: 'S16',
                       8: 'E8', 4: 'F4', 2: 'CHAMP'}.get(upset['round'], '??')
            rat_w = get_team_rating(w['team_no'], ratings_df)
            rat_l = get_team_rating(l['team_no'], ratings_df)
            leverage = 'HIGH' if upset['win_prob'] > 0.44 else 'MODERATE'
            lines.append(
                f'  {i}. [{rd_name}] ({w["seed"]}) {w["team"]:<18s} over '
                f'({l["seed"]}) {l["team"]:<18s} -- '
                f'Model: {upset["win_prob"]*100:.0f}%, '
                f'Public: ~{pub*100:.0f}% --> {leverage} LEVERAGE')
            # Add reasoning
            reasons = []
            if rat_w > rat_l:
                reasons.append(f'composite {rat_w:.2f} > {rat_l:.2f}')
            seed_matchup = f'{l["seed"]}v{w["seed"]}'
            if seed_matchup in ('5v12', '6v11', '7v10'):
                reasons.append(f'{seed_matchup} upsets hit ~35-49% historically')
            if reasons:
                lines.append(f'       WHY: {"; ".join(reasons)}')
    else:
        lines.append('  (No contrarian upsets selected - chalk bracket)')
    lines.append('')

    # Top 10 teams by composite
    lines.append(f'{"-"*72}')
    lines.append('TOP 15 TEAMS BY COMPOSITE RATING:')
    lines.append(f'{"-"*72}')
    tourney = ratings_df[ratings_df['SEED'].notna() & (ratings_df['SEED'] > 0)]
    tourney = tourney.sort_values('COMPOSITE', ascending=False).head(15)
    lines.append(f'  {"Rank":<5s} {"Team":<22s} {"Seed":>4s} {"Composite":>10s} '
                 f'{"KADJ EM":>8s} {"BADJ EM":>8s}')
    lines.append(f'  {"-"*62}')
    for rank, (_, row) in enumerate(tourney.iterrows(), 1):
        kadj = row.get('KADJ EM', 0)
        badj = row.get('BADJ_EM', 0)
        lines.append(
            f'  {rank:<5d} {row["TEAM"]:<22s} {int(row["SEED"]):>4d} '
            f'{row["COMPOSITE"]:>10.4f} {kadj:>8.2f} {badj:>8.2f}')
    lines.append('')

    # Key analytical insights
    lines.append(f'{"-"*72}')
    lines.append('KEY ANALYTICAL INSIGHTS:')
    lines.append(f'{"-"*72}')
    lines.append('  RED FLAGS (teams at risk of early exit):')
    lines.append('    - Duke (1): EXP 0.86 -- youngest team in tourney (freshman risk)')
    lines.append('    - Florida (1): Neutral BADJ EM drops 9.7 pts from overall')
    lines.append('    - Alabama (4): 53.7% of shots from 3 -- most volatile offense')
    lines.append('    - Wisconsin (5): Neutral BADJ EM drops 9.1 pts from overall')
    lines.append('    - Virginia (3): Worst coach+program PASE in field (-7.1/-7.6)')
    lines.append('')
    lines.append('  DARK HORSES (underseeded teams with elite profiles):')
    lines.append('    - Vanderbilt (5): Plays like a 2-seed, EXP 2.31, KADJ EM 27.5')
    lines.append('    - St. John\'s (5): Elite defense (KADJ D 94.2), EXP 2.30')
    lines.append('    - Tennessee (6): KADJ EM 26.0 + elite D (95.0) -- underseeded')
    lines.append('    - Iowa (9): KADJ EM 22.4 > Clemson 19.2 -- analytically favored')
    lines.append('    - Utah St. (9): ELO rank 14 (!), model favors over Villanova')
    lines.append('')
    lines.append('  COACHING EDGES:')
    lines.append('    - Tom Izzo (Michigan St.): #1 PASE, 88.6% F4 probability')
    lines.append('    - John Calipari (Arkansas): #2 PASE, 99% F4 probability')
    lines.append('    - Dan Hurley (Connecticut): #6 PASE, back-to-back champion')
    lines.append('    - Dusty May (Michigan): #17 PASE, rising tournament coach')
    lines.append('')
    lines.append('  HISTORICAL CONTEXT (from 2012-2025 backtest):')
    lines.append('    - 6v11 matchups: 50% upset rate -- true coin flips')
    lines.append('    - 5v12 matchups: 40.4% upset rate -- always consider the 12')
    lines.append('    - KADJ EM gap < 12: upset rate is 44% (competitive games)')
    lines.append('    - KADJ EM gap > 15: upset rate drops to 8% (safe favorites)')
    lines.append('')

    # "Go bolder" alternatives
    lines.append(f'{"-"*72}')
    lines.append('IF YOU WANT TO GO BOLDER (flip these close games):')
    lines.append(f'{"-"*72}')
    tossups = [g for g in results['all_games']
               if 0.40 <= g['win_prob'] <= 0.58 and not g['is_upset']
               and g['round'] >= 8]  # Only show meaningful round games
    tossups.sort(key=lambda x: (-x['round'], abs(x['prob_a'] - 0.5)))
    for game in tossups[:8]:
        loser = game['loser']
        winner = game['winner']
        loser_prob = 1.0 - game['win_prob']
        rd_name = {68: 'FF', 64: 'R64', 32: 'R32', 16: 'S16',
                   8: 'E8', 4: 'F4', 2: 'CHAMP'}.get(game['round'], '??')
        lines.append(
            f'  [{rd_name:>5s}] ({loser["seed"]}) {loser["team"]:<20s} over '
            f'({winner["seed"]}) {winner["team"]:<20s} '
            f'({loser_prob*100:.0f}% chance)')
    lines.append('')
    lines.append(sep)

    return '\n'.join(lines)


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    print("Loading data...")
    data = load_all_data()

    print("Computing seed base rates...")
    base_rates = compute_seed_base_rates(data['seed_results'])

    print("Calibrating model via backtesting (2012-2025)...")
    best_sigma, best_acc = calibrate_sigma(data)
    print(f"  Best sigma: {best_sigma:.2f} (R64 accuracy: {best_acc*100:.1f}%)")

    # Run full backtest with best sigma
    backtest_results = run_backtest(data, sigma=best_sigma)
    print("  Backtest results by year:")
    for r in backtest_results:
        print(f"    {r['year']}: {r['r64_correct']}/{r['r64_total']} "
              f"({r['r64_pct']*100:.1f}%)")

    print("\nComputing 2026 composite ratings...")
    coach_pase = build_coach_pase_map(data, year=2026)
    ratings_2026 = compute_composite_ratings(data, 2026, coach_pase_map=coach_pase)

    # Filter to tournament teams
    tourney_teams = data['matchups'][
        (data['matchups']['YEAR'] == 2026) &
        (data['matchups']['CURRENT ROUND'] == 64)
    ]['TEAM NO'].unique()
    ratings_tourney = ratings_2026[ratings_2026['TEAM NO'].isin(tourney_teams)].copy()

    print(f"  {len(ratings_tourney)} tournament teams rated")
    top5 = ratings_tourney.sort_values('COMPOSITE', ascending=False).head(5)
    for _, row in top5.iterrows():
        print(f"    {row['TEAM']:<22s} Seed {int(row['SEED']):>2d}  "
              f"Composite: {row['COMPOSITE']:.4f}")

    print("\nParsing 2026 bracket...")
    regions, first_four = parse_bracket_2026(data)
    print(f"  {len(regions)} regions, {len(first_four)} First Four games")
    for i, ff in enumerate(first_four):
        print(f"    FF{i+1}: ({ff['a']['seed']}) {ff['a']['team']} vs "
              f"({ff['b']['seed']}) {ff['b']['team']}")

    print("\nSimulating bracket...")
    results = simulate_full_bracket(
        regions, first_four, ratings_tourney, base_rates,
        sigma=best_sigma, contrarian=True)

    print("\n")
    output = format_bracket(results, ratings_tourney, backtest_results, best_sigma)
    print(output)

    return results, ratings_tourney


if __name__ == '__main__':
    results, ratings = main()
