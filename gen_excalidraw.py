#!/usr/bin/env python3
"""Generate the Excalidraw architecture diagram with proper bindings."""
import json

elements = []
_id_counter = [0]

def uid(prefix="el"):
    _id_counter[0] += 1
    return f"{prefix}_{_id_counter[0]}"

def rect(x, y, w, h, bg="#a5d8ff", stroke="#1971c2", sw=2, rough=1, opacity=100):
    rid = uid("r")
    return {"id": rid, "type": "rectangle", "x": x, "y": y, "width": w, "height": h,
            "angle": 0, "strokeColor": stroke, "backgroundColor": bg,
            "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": "solid",
            "roughness": rough, "opacity": opacity, "groupIds": [], "frameId": None,
            "roundness": {"type": 3}, "seed": _id_counter[0]*7, "version": 1,
            "versionNonce": _id_counter[0]*13, "isDeleted": False,
            "boundElements": [], "updated": 1710700000000, "link": None, "locked": False}

def text(content, x, y, w, h, fs=13, ff=3, align="left", valign="top", color="#1e1e1e", container=None):
    tid = uid("t")
    return {"id": tid, "type": "text", "x": x, "y": y, "width": w, "height": h,
            "angle": 0, "strokeColor": color, "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
            "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": None, "seed": _id_counter[0]*7+1, "version": 1,
            "versionNonce": _id_counter[0]*13+1, "isDeleted": False,
            "boundElements": None, "updated": 1710700000000, "link": None, "locked": False,
            "text": content, "fontSize": fs, "fontFamily": ff, "textAlign": align,
            "verticalAlign": valign, "containerId": container,
            "originalText": content, "autoResize": True, "lineHeight": 1.25}

def arrow(x, y, dx, dy, color="#1e1e1e", sw=2, style="solid", src=None, tgt=None):
    aid = uid("a")
    sb = {"elementId": src, "focus": 0, "gap": 1} if src else None
    eb = {"elementId": tgt, "focus": 0, "gap": 1} if tgt else None
    return {"id": aid, "type": "arrow", "x": x, "y": y, "width": abs(dx), "height": abs(dy),
            "angle": 0, "strokeColor": color, "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": style,
            "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": {"type": 2}, "seed": _id_counter[0]*7+2, "version": 1,
            "versionNonce": _id_counter[0]*13+2, "isDeleted": False,
            "boundElements": None, "updated": 1710700000000, "link": None, "locked": False,
            "points": [[0, 0], [dx, dy]], "lastCommittedPoint": None,
            "startBinding": sb, "endBinding": eb,
            "startArrowhead": None, "endArrowhead": "arrow", "elbowed": False}

def diamond(x, y, w, h, bg="#ffc9c9", stroke="#c92a2a"):
    did = uid("d")
    return {"id": did, "type": "diamond", "x": x, "y": y, "width": w, "height": h,
            "angle": 0, "strokeColor": stroke, "backgroundColor": bg,
            "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": {"type": 2}, "seed": _id_counter[0]*7+3, "version": 1,
            "versionNonce": _id_counter[0]*13+3, "isDeleted": False,
            "boundElements": [], "updated": 1710700000000, "link": None, "locked": False}

def box_with_text(x, y, w, content, fs=13, bg="#a5d8ff", stroke="#1971c2",
                  ff=3, align="left", valign="top", color="#1e1e1e", sw=2, rough=1, pad=10):
    """Create a rectangle with properly sized bound text."""
    lines = content.count('\n') + 1
    line_h = fs * 1.25
    text_h = lines * line_h
    h = max(text_h + pad*2, 40)
    r = rect(x, y, w, h, bg=bg, stroke=stroke, sw=sw, rough=rough)
    t = text(content, x+pad, y+pad, w-pad*2, text_h, fs=fs, ff=ff,
             align=align, valign=valign, color=color, container=r["id"])
    r["boundElements"].append({"id": t["id"], "type": "text"})
    return r, t, h

def bind_arrow(a, src_r, tgt_r):
    """Set up arrow bindings between source and target rectangles."""
    if src_r:
        a["startBinding"] = {"elementId": src_r["id"], "focus": 0, "gap": 1}
        src_r["boundElements"].append({"id": a["id"], "type": "arrow"})
    if tgt_r:
        a["endBinding"] = {"elementId": tgt_r["id"], "focus": 0, "gap": 1}
        tgt_r["boundElements"].append({"id": a["id"], "type": "arrow"})

# ============ BACKGROUNDS ============
elements.append(rect(0, 85, 1280, 190, bg="#dbe4ff", stroke="transparent", sw=0, rough=0, opacity=40))
elements.append(rect(0, 370, 1280, 275, bg="#ebfbee", stroke="transparent", sw=0, rough=0, opacity=35))
elements.append(rect(0, 680, 1280, 240, bg="#fff5f5", stroke="transparent", sw=0, rough=0, opacity=40))
elements.append(rect(60, 955, 1160, 250, bg="#f3f0ff", stroke="transparent", sw=0, rough=0, opacity=40))
elements.append(rect(1310, 85, 730, 1120, bg="#fff9db", stroke="transparent", sw=0, rough=0, opacity=25))

# ============ TITLE ============
r, t, _ = box_with_text(200, 10, 880,
    "MARCH MADNESS 2026 BRACKET PREDICTOR - SYSTEM ARCHITECTURE",
    fs=22, bg="#343a40", stroke="#1e1e1e", ff=1, align="center", valign="middle", color="#ffffff", pad=12)
elements.extend([r, t])

# ============ DATA SOURCE LABELS ============
elements.append(text("10 CSV DATA SOURCES (2008-2026)", 15, 88, 300, 18, fs=14, ff=1, color="#364fc7"))

# ============ DATA SOURCES ============
ds_info = [
    ("KenPom Barttorvik\nKADJ EM, KADJ O, KADJ D\nBADJ EM, EXP, TOV%\nBARTHAG, TALENT", 15, 108),
    ("Barttorvik Neutral\nBADJ EM\n(neutral court only)", 260, 108),
    ("EvanMiya\nRELATIVE RATING\nKILLSHOTS MARGIN\nINJURY RANK", 505, 108),
    ("RPPF Ratings\nRADJ EM\nRADJ O, RADJ D", 750, 108),
    ("Shooting Splits\nTHREES SHARE\nTHREES FG%, FG%D", 995, 108),
    ("Resumes\nNET, ELO, WAB RANK\nQ1 W, BID TYPE", 15, 198),
    ("Seed Results\nHistorical base rates\nby seed (R64 to Champ)", 260, 198),
    ("Coach Results\nCOACH, PASE\nCHAMP%, F4%", 505, 198),
    ("Team Results\nProgram PASE\nF4%, CHAMP%", 750, 198),
    ("Tournament Matchups\n2026 bracket structure\n+ historical results", 995, 198),
]
ds_rects = []
for info, x, y in ds_info:
    r, t, _ = box_with_text(x, y, 230, info, fs=12, bg="#a5d8ff", stroke="#1971c2", pad=8)
    elements.extend([r, t])
    ds_rects.append(r)

# ============ MERGE ============
r_merge, t_merge, _ = box_with_text(150, 300, 980,
    "DATA LOADING & MERGE  --  Join Key: TEAM NO + YEAR (consistent across all 10 CSV files)",
    fs=15, bg="#d0bfff", stroke="#5f3dc4", ff=1, align="center", valign="middle", pad=12)
elements.extend([r_merge, t_merge])

# Arrow: data sources -> merge
a = arrow(640, 278, 0, 18, color="#364fc7", sw=3, tgt=r_merge["id"])
r_merge["boundElements"].append({"id": a["id"], "type": "arrow"})
elements.append(a)

# ============ SECTION LABEL ============
elements.append(text("PROCESSING & MODELING", 15, 375, 250, 18, fs=14, ff=1, color="#2f9e44"))

# ============ COMPOSITE RATING ============
r_comp, t_comp, h_comp = box_with_text(10, 395, 570,
    "COMPOSITE RATING ENGINE  (Z-Score Normalized Weighted Average)",
    fs=15, bg="#b2f2bb", stroke="#2f9e44", ff=1, align="center", valign="middle", pad=12)
elements.extend([r_comp, t_comp])

r_t1, t_t1, h_t1 = box_with_text(10, 395+h_comp+8, 275,
    "TIER 1: Core Efficiency\n(85% of total weight)\n\n  KADJ EM ............ 0.25\n  BADJ EM ............ 0.20\n  Neutral BADJ EM .... 0.20\n  RADJ EM ............ 0.10\n  Relative Rating .... 0.10",
    fs=12, bg="#d3f9d8", stroke="#2f9e44", pad=10)
elements.extend([r_t1, t_t1])

r_t2, t_t2, h_t2 = box_with_text(305, 395+h_comp+8, 275,
    "TIER 2: Adjustments\n(15% of total weight)\n\n  Defense premium .... 0.040\n  Neutral delta ...... 0.030\n  Experience ......... 0.025\n  TOV discipline ..... 0.020\n  3PT stability ...... 0.015\n  Coach PASE ......... 0.020",
    fs=12, bg="#d3f9d8", stroke="#2f9e44", pad=10)
elements.extend([r_t2, t_t2])

# Arrow: merge -> composite
a1 = arrow(300, 300+50, 0, 395-350, color="#2f9e44", src=r_merge["id"], tgt=r_comp["id"])
bind_arrow(a1, r_merge, r_comp)
elements.append(a1)

# ============ WIN PROBABILITY ============
r_wp, t_wp, h_wp = box_with_text(620, 395, 340,
    "WIN PROBABILITY MODEL",
    fs=15, bg="#ffec99", stroke="#e67700", ff=1, align="center", valign="middle", pad=12)
elements.extend([r_wp, t_wp])

r_wpd, t_wpd, h_wpd = box_with_text(620, 395+h_wp+8, 340,
    "Logistic Model:\n  P(A wins) = 1 / (1 + 10^(-diff / sigma))\n  sigma = 3.40 (calibrated via backtest)\n\nBayesian Blend:\n  85% model probability\n  + 15% historical seed base rate\n\nRound Amplification (favorites edge):\n  R64: 1.00x  R32: 1.02x  S16: 1.05x\n  E8: 1.08x   F4: 1.10x   Champ: 1.12x",
    fs=12, bg="#fff3bf", stroke="#e67700", pad=10)
elements.extend([r_wpd, t_wpd])

# Arrow: merge -> win prob
a2 = arrow(790, 300+50, 0, 395-350, color="#e67700", src=r_merge["id"], tgt=r_wp["id"])
bind_arrow(a2, r_merge, r_wp)
elements.append(a2)

# ============ BACKTESTING ============
r_bt, t_bt, h_bt = box_with_text(1000, 395, 265,
    "BACKTESTING (2012-2025)",
    fs=15, bg="#ffec99", stroke="#e67700", ff=1, align="center", valign="middle", pad=12)
elements.extend([r_bt, t_bt])

r_btd, t_btd, h_btd = box_with_text(1000, 395+h_bt+8, 265,
    "Calibrates sigma parameter\n13 years tested (excl 2020)\n\nAvg R64 accuracy: 73.7%\nRange: 62.5% - 87.5%\n\nBest: 2017 (87.5%)\n      2014, 2025 (81.2%)\nWorst: 2024 (62.5%)\n\nTarget: 72-76%  [MET]",
    fs=12, bg="#fff3bf", stroke="#e67700", pad=10)
elements.extend([r_btd, t_btd])

# Arrow: merge -> backtest
a3 = arrow(1100, 300+50, 32, 395-350, color="#e67700", src=r_merge["id"], tgt=r_bt["id"])
bind_arrow(a3, r_merge, r_bt)
elements.append(a3)

# Arrow: backtest -> win prob (feedback, dashed)
a_bt_wp = arrow(998, 395+h_bt+80, -36, 0, color="#e67700", sw=2, style="dashed",
                src=r_btd["id"], tgt=r_wpd["id"])
bind_arrow(a_bt_wp, r_btd, r_wpd)
elements.append(a_bt_wp)
elements.append(text("sigma", 966, 395+h_bt+65, 30, 14, fs=11, ff=3, color="#e67700"))

# ============ SIM LABEL ============
elements.append(text("SIMULATION & OPTIMIZATION", 15, 685, 300, 18, fs=14, ff=1, color="#c92a2a"))

# ============ BRACKET SIMULATION ============
r_sim, t_sim, h_sim = box_with_text(10, 705, 570,
    "BRACKET SIMULATION ENGINE\n\n  First Four: 4 play-in games\n    --> R64: 32 games (4 regions x 8)\n      --> R32: 16 games\n        --> Sweet 16: 8 games\n          --> Elite Eight: 4 games\n            --> Final Four: 2 games\n              --> Championship: 1 game\n\n  Total: 67 games | Winners feed forward each round",
    fs=13, bg="#ffc9c9", stroke="#c92a2a", pad=10)
elements.extend([r_sim, t_sim])

# Arrow: composite -> sim
a_c_s = arrow(295, 395+h_comp+8+max(h_t1,h_t2), 0, 705-(395+h_comp+8+max(h_t1,h_t2)),
              color="#c92a2a", src=r_t1["id"], tgt=r_sim["id"])
bind_arrow(a_c_s, r_t1, r_sim)
elements.append(a_c_s)
elements.append(text("ratings", 305, 705-25, 60, 14, fs=11, ff=3, color="#c92a2a"))

# Arrow: win prob -> sim
a_w_s = arrow(750, 395+h_wp+8+h_wpd, -160, 705-(395+h_wp+8+h_wpd),
              color="#c92a2a", src=r_wpd["id"], tgt=r_sim["id"])
bind_arrow(a_w_s, r_wpd, r_sim)
elements.append(a_w_s)
elements.append(text("probabilities", 620, 705-25, 100, 14, fs=11, ff=3, color="#c92a2a"))

# ============ POOL VALUE ============
r_pool, t_pool, h_pool = box_with_text(620, 705, 645,
    "POOL VALUE OPTIMIZER (KEY FOR WINNING POOLS)\n\nUpset Budget per round:\n  R64: max 4 | R32: max 2 | S16: max 1 | E8: max 1\n\nUpset Selection Criteria (seed-specific):\n  6v11: model prob >= 44%  (historical upset rate: 50%!)\n  7v10: model prob >= 46%  (historical upset rate: 37%)\n  5v12: model prob >= 40%  (historical upset rate: 40%)\n  4v13: model prob >= 38%  (rarer, high leverage)\n  R32+: prob >= 46%, composite within 0.8 std dev\n\nLeverage = P(win) x Round Points / Est. Public Pick Rate\nPick upset when: leverage(upset) > leverage(chalk) AND thresholds met",
    fs=12, bg="#ffe3e3", stroke="#c92a2a", pad=10)
elements.extend([r_pool, t_pool])

# Arrow: pool -> sim
a_p_s = arrow(618, 800, -28, 0, color="#c92a2a", src=r_pool["id"], tgt=r_sim["id"])
bind_arrow(a_p_s, r_pool, r_sim)
elements.append(a_p_s)
elements.append(text("upset picks", 582, 785, 40, 14, fs=11, ff=3, color="#c92a2a", align="right"))

# ============ OUTPUT ============
r_out, t_out, h_out = box_with_text(80, 970, 1120,
    "FINAL BRACKET OUTPUT\n\nCHAMPION: (1) Michigan  |  Composite #1 (1.543)  |  KADJ EM 37.6  |  Defense 89.0  |  EXP 1.95\nFINAL FOUR: Duke (East) | Houston (South) | Arizona (West) | Michigan (Midwest)\n\n5 Contrarian Upset Picks:\n  1. VCU (11) over UNC (6) -- R64, 48% model, 6v11 historically 50%\n  2. Texas A&M (10) over Saint Mary's (7) -- R64, 47% model, 7v10 classic spot\n  3. NC State (11) over BYU (6) -- R64, 46% model, ACC battle-tested 11-seed\n  4. Santa Clara (10) over Kentucky (7) -- R64, 48% model, ELO 24 > Kentucky 45\n  5. Tennessee (6) over Virginia (3) -- R32, 50% model, Virginia worst PASE in field\n\nBacktest: 73.7% R64 accuracy | Path probability: 6.06% | Bracket log-confidence: -31.28",
    fs=12, bg="#e5dbff", stroke="#5f3dc4", sw=3, pad=12)
elements.extend([r_out, t_out])

# Arrow: sim -> output
a_s_o = arrow(400, 705+h_sim, 200, 970-(705+h_sim), color="#5f3dc4", sw=3,
              src=r_sim["id"], tgt=r_out["id"])
bind_arrow(a_s_o, r_sim, r_out)
elements.append(a_s_o)

# ============ RIGHT SIDE: DECISION DETAILS ============
elements.append(text("DECISION DETAILS & KEY DATA POINTS", 1325, 88, 400, 20, fs=16, ff=1, color="#e67700"))

# -- Composite comparison --
r_ce, t_ce, _ = box_with_text(1325, 118, 700,
    "WHY MICHIGAN #1 IN COMPOSITE (despite Duke's highest KADJ EM)\n\n                   KADJ EM   BADJ EM   Neutral   RADJ EM   RelRtg    KADJ D    EXP\n  Michigan (1)      37.59     36.59     38.10     38.30     34.50     89.03    1.95\n  Arizona  (1)      37.66     35.53     38.40     38.60     32.05     90.02    1.41\n  Duke     (1)      38.90     37.32     32.90     39.90     34.83     89.06    0.86\n\n  Duke leads raw KADJ EM but DROPS 6 pts on neutral courts (32.9 vs 38.1 Michigan)\n  Michigan: best EXP (1.95 veterans), best Killshots (+1.00), #1 Injury Rank\n  Arizona: best neutral-court BADJ EM (38.4), best pure defense (KADJ D 90.0)\n  Duke EXP 0.86 = youngest team in tourney -- historically a March liability\n  Composite weights neutral performance (20%) and experience (2.5%) --> Michigan edges Duke",
    fs=11, bg="#d3f9d8", stroke="#2f9e44", pad=10)
elements.extend([r_ce, t_ce])

# -- Upset decision diamond --
d = diamond(1480, 345, 200, 90, bg="#ffc9c9", stroke="#c92a2a")
dt = text("Pick upset?\n(per game)", 1530, 370, 100, 35, fs=13, ff=1,
          align="center", valign="middle", container=d["id"])
d["boundElements"].append({"id": dt["id"], "type": "text"})
elements.extend([d, dt])

# NO branch
r_no, t_no, _ = box_with_text(1325, 460, 155,
    "NO: Skip if\n8v9 matchup\nor seed gap <= 1\nor budget = 0",
    fs=11, bg="#dee2e6", stroke="#868e96", pad=8)
elements.extend([r_no, t_no])

a_no = arrow(1500, 435, -70, 22, color="#868e96", src=d["id"], tgt=r_no["id"])
bind_arrow(a_no, d, r_no)
elements.append(a_no)
elements.append(text("NO", 1410, 438, 20, 14, fs=12, ff=1, color="#868e96"))

# YES branch -> thresholds
r_thr, t_thr, h_thr = box_with_text(1510, 460, 300,
    "Check Seed Thresholds:\n\n  R64  5v12: prob >= 40%, diff < 1.2 std\n  R64  6v11: prob >= 44%\n  R64  7v10: prob >= 46%\n  R64  4v13: prob >= 38%, diff < 0.8 std\n  R32  all:  prob >= 46%, diff < 0.8 std\n  S16+ all:  prob >= 49%, gap >= 3 seeds\n\nBudget caps: R64:4  R32:2  S16:1  E8:1",
    fs=11, bg="#fff5f5", stroke="#c92a2a", pad=8)
elements.extend([r_thr, t_thr])

a_yes = arrow(1600, 435, 60, 22, color="#c92a2a", src=d["id"], tgt=r_thr["id"])
bind_arrow(a_yes, d, r_thr)
elements.append(a_yes)
elements.append(text("YES", 1625, 438, 25, 14, fs=12, ff=1, color="#c92a2a"))

# Threshold -> Rank by leverage
r_rank, t_rank, _ = box_with_text(1840, 465, 170,
    "Rank by Leverage\n\nLeverage =\n  P(win) x Points\n  / Public Pick Rate\n\nSelect top N\nper budget",
    fs=11, bg="#ffe3e3", stroke="#c92a2a", pad=8)
elements.extend([r_rank, t_rank])

a_tr = arrow(1812, 510, 25, 0, color="#c92a2a", src=r_thr["id"], tgt=r_rank["id"])
bind_arrow(a_tr, r_thr, r_rank)
elements.append(a_tr)

# -- Red Flags --
r_rf, t_rf, h_rf = box_with_text(1325, 650, 340,
    "RED FLAGS (early exit risk)\n\nDuke (1):  EXP 0.86 = youngest team\n           Neutral BADJ drops 6.0 pts\nFlorida (1): Neutral drops 9.7 pts!\n             Inflated by home games\nAlabama (4): 53.7% shots from 3PT\n             Most volatile offense in field\nVirginia (3): Coach PASE -7.1 (#331)\n              Worst coach+program combo\nWisconsin (5): Neutral drops 9.1 pts\nKansas (4): Coach PASE -3.7\n            Blue blood, March dud",
    fs=11, bg="#fff5f5", stroke="#e03131", pad=8)
elements.extend([r_rf, t_rf])

# -- Dark Horses --
r_dh, t_dh, h_dh = box_with_text(1685, 650, 340,
    "DARK HORSES (underseeded)\n\nVanderbilt (5): KADJ 27.5 = 2-seed level\n  EXP 2.31, elite neutral performance\nSt. John's (5): KADJ D 94.2 (elite D)\n  EXP 2.30, Pitino PASE +2.6\nTennessee (6): KADJ 26.0 + D 95.0\n  Underseeded, composite beats Virginia\nIowa (9): KADJ 22.4 > Clemson 19.2\n  9-seed analytically BETTER than 8\nUtah St. (9): ELO rank #14 (!)\n  Model favors over Villanova (8)\nHouston (2): #6 composite as 2-seed\n  Beats Florida (1) in E8 on data",
    fs=11, bg="#ebfbee", stroke="#2f9e44", pad=8)
elements.extend([r_dh, t_dh])

# -- Historical patterns --
r_hist, t_hist, h_hist = box_with_text(1325, 650+max(h_rf,h_dh)+15, 340,
    "HISTORICAL UPSET RATES (2012-2025)\n\n Seed   Games  Upsets  Rate    EM Gap\n 1v16     52       2    3.8%    ~33\n 2v15     52       7   13.5%    ~24\n 3v14     52       7   13.5%    ~16\n 4v13     52      10   19.2%    ~13\n 5v12     52      21   40.4%    ~8\n 6v11     52      26   50.0%    COIN FLIP\n 7v10     51      19   37.3%    ~2\n 8v9      52      26   50.0%    COIN FLIP\n\n KEY: KADJ EM gap < 12 --> 44% upset rate\n      KADJ EM gap > 15 --> only 8% upsets",
    fs=11, bg="#fff3bf", stroke="#e67700", pad=8)
elements.extend([r_hist, t_hist])

# -- Coaching factor --
r_coach, t_coach, h_coach = box_with_text(1685, 650+max(h_rf,h_dh)+15, 340,
    "COACHING FACTOR (PASE = Perf vs Seed Exp)\n\nBEST (overperform in March):\n  Izzo (MSU):      +10.3   #1 of 332\n  Calipari (ARK):   +9.8   #2\n  Hurley (UCONN):   +5.8   #6 B2B champ\n  Few (GONZ):       +4.7   #10 consistent\n  May (MICH):       +3.5   #17 rising\n  Pitino (STJ):     +2.6   #22 veteran\n\nWORST (underperform in March):\n  Bennett (UVA):    -7.1   #331 of 332!\n  Self (KU):        -3.7   #327\n  Painter (PUR):    -2.3   #318\n  Barnes (TENN):    -3.0   #323 0 F4s",
    fs=11, bg="#e5dbff", stroke="#5f3dc4", pad=8)
elements.extend([r_coach, t_coach])

# -- Bracket path --
r_path, t_path, h_path = box_with_text(1325, 650+max(h_rf,h_dh)+15+max(h_hist,h_coach)+15, 700,
    "BRACKET PATH TO CHAMPIONSHIP\n\n EAST:    Duke(1) > Siena > OhioSt > StJohns > MichSt > UConn -----------------------> DUKE\n SOUTH:   Florida(1) > PrVwA&M > Iowa > Vandy > Illinois | Houston(2) > Idaho > TexA&M > Hou > HOUSTON beats Florida in E8!\n WEST:    Arizona(1) > LIU > UtahSt > Arkansas > Purdue ---------------------------------> ARIZONA\n MIDWEST: Michigan(1) > UMBC > Georgia > Alabama > IowaSt -----------------------------> MICHIGAN\n\n FINAL FOUR: Duke beats Houston (53.7%) | Michigan beats Arizona (50.5%)\n CHAMPIONSHIP: Michigan beats Duke (52.0%)  -->  MICHIGAN WINS IT ALL\n\n KEY CONTRARIAN MOVE: Houston(2) over Florida(1) in E8 -- composite 1.21 vs 1.05, data says Houston is better team",
    fs=11, bg="#f8f9fa", stroke="#1e1e1e", pad=10)
elements.extend([r_path, t_path])

# ============ WRITE FILE ============
doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "bracket_predictor",
    "elements": elements,
    "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
    "files": {}
}

out = "/Users/alay.deliwala/Downloads/march-madness-data/bracket_predictor_architecture.excalidraw"
with open(out, "w") as f:
    json.dump(doc, f, indent=2)
print(f"Generated {len(elements)} elements -> {out}")
