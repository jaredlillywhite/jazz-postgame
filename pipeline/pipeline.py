"""Core stats pipeline for the Jazz postgame dashboard.

Data: NBA Stats API via nba_api (V3 endpoints — the V2 boxscore/play-by-play
endpoints no longer return data). Free-throw trips are counted from the
play-by-play, never estimated, for the featured game.
"""
import json
import re
import time
import warnings

warnings.filterwarnings("ignore")

JAZZ_ID = 1610612762
# Trips per free-throw attempt, measured across 56 team-games in Oct 2026
# (mean 0.556, median 0.56). Used ONLY to estimate the league distribution
# for shot-opportunity percentiles; the featured game's trips are counted.
TRIPS_PER_FTA = 0.556


def _call(fn, label, tries=4):
    for i in range(tries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - NBA API is flaky; retry
            print(f"retry {label} ({i + 1}): {type(exc).__name__}")
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"failed: {label}")


def current_season():
    import datetime
    today = datetime.date.today()
    if today.month >= 10:
        return f"{today.year}-{str(today.year + 1)[2:]}"
    return f"{today.year - 1}-{str(today.year)[2:]}"


def jazz_finals(season):
    """Game IDs of completed Jazz games this season, oldest first."""
    from nba_api.stats.endpoints import teamgamelog
    df = _call(lambda: teamgamelog.TeamGameLog(team_id=JAZZ_ID, season=season),
               "teamgamelog").get_data_frames()[0]
    games = []
    for row in df.to_dict("records"):
        if row["WL"] in ("W", "L"):
            games.append({
                "game_id": str(row["Game_ID"]),
                "date": str(row["GAME_DATE"]),
                "matchup": row["MATCHUP"],
            })
    return sorted(games, key=lambda g: g["date"])


def fetch_game(game_id):
    """Box score, play-by-play and shot charts for one game."""
    from nba_api.stats.endpoints import (
        boxscoretraditionalv3, playbyplayv3, shotchartdetail)
    box = _call(
        lambda: boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id),
        f"box-{game_id}").get_data_frames()
    teams = {r["teamTricode"]: r for r in box[2].to_dict("records")}
    players = box[0].to_dict("records")
    pbp = _call(
        lambda: playbyplayv3.PlayByPlayV3(game_id=game_id),
        f"pbp-{game_id}").get_data_frames()[0]
    pbp = sorted(pbp.to_dict("records"), key=lambda a: a["actionNumber"])
    shots = {}
    for tri, info in teams.items():
        sc = _call(
            lambda t=info["teamId"]: shotchartdetail.ShotChartDetail(
                team_id=t, player_id=0, game_id_nullable=game_id,
                context_measure_simple="FGA"),
            f"shots-{game_id}-{tri}").get_data_frames()[0]
        shots[tri] = sc.to_dict("records")
    return teams, pbp, shots, players


def count_trips(pbp):
    """Free-throw trips per team, from PBP descriptions.

    A new trip starts on 'Free Throw 1 of N' or a technical/flagrant FT;
    '2 of N' / '3 of N' continue the current trip.
    """
    trips = {}
    for a in pbp:
        if a["actionType"] != "Free Throw":
            continue
        d = a["description"] or ""
        if ("1 of" in d) or ("Technical" in d) or ("Flagrant" in d):
            t = a["teamTricode"] or "UNK"
            trips[t] = trips.get(t, 0) + 1
    return trips


def team_metrics(box, trips, opp_drb):
    fga = box["fieldGoalsAttempted"]
    fta = box["freeThrowsAttempted"]
    tov = box["turnovers"]
    orb = box["reboundsOffensive"]
    pts = box["points"]
    poss = fga - orb + tov + 0.44 * fta
    tso = fga + trips
    return {
        "pts": pts, "fga": fga, "fta": fta, "tov": tov, "orb": orb,
        "drb": box["reboundsDefensive"], "ftm": box["freeThrowsMade"],
        "trips": trips, "poss": round(poss, 1), "tso": tso,
        "ppo": round(pts / tso, 3) if tso else None,
        "tov_pct": round(100 * tov / poss, 1) if poss else None,
        "orb_pct": round(100 * orb / (orb + opp_drb), 1) if orb + opp_drb else None,
        "ftr": round(fta / fga, 3) if fga else None,
        "ts_pct": round(pts / (2 * (fga + 0.44 * fta)), 3) if fga else None,
    }


def shot_quality(shots, zone_avg):
    exp_pts, act_pts = 0.0, 0
    for s in shots:
        val = 3 if s["SHOT_TYPE"] == "3PT Field Goal" else 2
        exp_pts += zone_avg.get(s["SHOT_ZONE_BASIC"], 0.45) * val
        act_pts += val if s["SHOT_MADE_FLAG"] else 0
    fga = len(shots)
    return {
        "fga": fga, "exp_pts": round(exp_pts, 1), "act_fg_pts": act_pts,
        "luck_pts": round(act_pts - exp_pts, 1),
        "shot_quality": round(exp_pts / fga, 3) if fga else None,
    }


def _parse_clock(clock):
    m = re.match(r"PT(\d+)M([\d.]+)S", clock or "")
    if not m:
        return None
    return int(m.group(1)) * 60 + float(m.group(2))


def _clock_str(period, clock):
    rem = _parse_clock(clock)
    if rem is None:
        return f"Q{period}"
    return f"Q{period} {int(rem // 60)}:{int(rem % 60):02d}"


def quarter_splits(pbp, home, away):
    """Per-period framework stats. Rebounds are classified by comparing the
    rebounding team to the team that missed the shot just before."""
    from collections import defaultdict
    q = defaultdict(lambda: defaultdict(int))
    prev_h = prev_a = None
    last_miss = None
    for a in pbp:
        t, p = a["teamTricode"], a["period"]
        at, desc = a["actionType"], a["description"] or ""
        if a["isFieldGoal"]:
            q[(p, t)]["fga"] += 1
            if a["shotResult"] == "Made":
                if a["shotValue"] == 3:
                    q[(p, t)]["tpm"] += 1
            else:
                last_miss = t
        elif at == "Free Throw":
            q[(p, t)]["fta"] += 1
            if "MISS" not in desc:
                q[(p, t)]["ftm"] += 1
            else:
                last_miss = t
            if ("1 of" in desc) or ("Technical" in desc):
                q[(p, t)]["trips"] += 1
        elif at == "Turnover":
            q[(p, t)]["tov"] += 1
        elif at == "Rebound" and t:
            if t == last_miss:
                q[(p, t)]["orb"] += 1
            else:
                q[(p, t)]["drb"] += 1
        sh, sa = a["scoreHome"], a["scoreAway"]
        if sh == "" or sa == "":
            continue
        sh, sa = int(sh), int(sa)
        dh = sh - prev_h if prev_h is not None else 0
        da = sa - prev_a if prev_a is not None else 0
        if dh or da:
            q[(p, home if dh else away)]["pts"] += dh or da
        prev_h, prev_a = sh, sa

    def metrics(s, opp_drb):
        fga, fta, tov, orb = s["fga"], s["fta"], s["tov"], s["orb"]
        poss = fga - orb + tov + 0.44 * fta
        tso = fga + s["trips"]
        return {"pts": s["pts"], "fga": fga, "fta": fta, "tov": tov,
                "orb": orb, "trips": s["trips"], "tso": tso,
                "ppo": round(s["pts"] / tso, 3) if tso else None,
                "tov_pct": round(100 * tov / poss, 1) if poss else None,
                "orb_pct": round(100 * orb / (orb + opp_drb), 1) if orb + opp_drb else None,
                "ftr": round(fta / fga, 3) if fga else None,
                "ts_pct": round(s["pts"] / (2 * (fga + 0.44 * fta)), 3) if fga else None}

    periods = sorted({p for p, _ in q})
    out = {}
    for p in periods:
        out[p] = {
            home: metrics(q[(p, home)], q[(p, away)]["drb"]),
            away: metrics(q[(p, away)], q[(p, home)]["drb"]),
        }
    return out


def detect_runs(pbp, home, away, threshold=10):
    """Runs = stretches where the differential (home perspective) swings
    >= threshold from its previous extreme. Drivers counted from the PBP
    inside each window."""
    scoring = []
    prev_h = prev_a = None
    for a in pbp:
        sh, sa = a["scoreHome"], a["scoreAway"]
        if sh == "" or sa == "":
            continue
        sh, sa = int(sh), int(sa)
        dh = sh - prev_h if prev_h is not None else 0
        da = sa - prev_a if prev_a is not None else 0
        if dh or da:
            rem = _parse_clock(a["clock"])
            elapsed = ((a["period"] - 1) * 12 + (720 - rem) / 60
                       if rem is not None else (a["period"] - 1) * 12)
            scoring.append({"elapsed": round(elapsed, 2), "diff": sh - sa,
                            "team": home if dh else away, "pts": dh or da,
                            "action": a["actionNumber"], "period": a["period"],
                            "clock": a["clock"],
                            "label": _clock_str(a["period"], a["clock"])})
        prev_h, prev_a = sh, sa
    if not scoring:
        return [], []

    diffs = [0] + [s["diff"] for s in scoring]
    runs, min_v, max_v, min_i, max_i = [], 0, 0, -1, -1
    for i in range(1, len(diffs)):
        d = diffs[i]
        if d < min_v:
            min_v, min_i = d, i - 1
        if d > max_v:
            max_v, max_i = d, i - 1
        if d - min_v >= threshold:
            runs.append((home, min_i, i - 1))
            min_v = max_v = d
            min_i = max_i = i - 1
        elif max_v - d >= threshold:
            runs.append((away, max_i, i - 1))
            min_v = max_v = d
            min_i = max_i = i - 1

    cards = []
    for team, si, ei in runs:
        window = scoring[si + 1: ei + 1] if si >= 0 else scoring[: ei + 1]
        h_pts = sum(s["pts"] for s in window if s["team"] == home)
        a_pts = sum(s["pts"] for s in window if s["team"] == away)
        opp = away if team == home else home
        a0 = scoring[si]["action"] if si >= 0 else 0
        a1 = scoring[ei]["action"]
        lm, w_orb, w_opp_tov, w_tpm, w_ftm, w_trips = None, 0, 0, 0, 0, 0
        for a in pbp:
            if not (a0 < a["actionNumber"] <= a1):
                continue
            t, at, desc = a["teamTricode"], a["actionType"], a["description"] or ""
            if a["isFieldGoal"]:
                if a["shotResult"] == "Made":
                    if a["shotValue"] == 3 and t == team:
                        w_tpm += 1
                else:
                    lm = t
            elif at == "Free Throw":
                if "MISS" in desc:
                    lm = t
                elif t == team:
                    w_ftm += 1
                if ("1 of" in desc or "Technical" in desc) and t == team:
                    w_trips += 1
            elif at == "Turnover" and t == opp:
                w_opp_tov += 1
            elif at == "Rebound" and t == team and t == lm:
                w_orb += 1
        drivers = []
        if w_orb:
            drivers.append(f"{w_orb} offensive rebound{'s' if w_orb > 1 else ''}")
        if w_opp_tov:
            drivers.append(f"{w_opp_tov} forced turnover{'s' if w_opp_tov > 1 else ''}")
        if w_tpm:
            drivers.append(f"{w_tpm} three{'s' if w_tpm > 1 else ''}")
        if w_ftm:
            drivers.append(f"{w_ftm} made free throw{'s' if w_ftm > 1 else ''} ({w_trips} trips)")
        start = scoring[si] if si >= 0 else None
        cards.append({
            "team": team,
            "start": start["label"] if start else "Tip-off",
            "end": scoring[ei]["label"],
            "duration_min": round(scoring[ei]["elapsed"] - (start["elapsed"] if start else 0), 1),
            "home_pts": h_pts, "away_pts": a_pts,
            "start_diff": diffs[si + 1] if si >= 0 else 0,
            "end_diff": diffs[ei + 1],
            "start_elapsed": start["elapsed"] if start else 0.0,
            "end_elapsed": scoring[ei]["elapsed"],
            "drivers": drivers,
        })
    series = [[s["elapsed"], s["diff"]] for s in scoring]
    return cards, series


def league_percentiles(season, featured):
    """Percentile of each featured metric vs all team-games this season.

    TOV%/ORB%/FTr/TS% come exactly from the league game log. TSO/PPO for the
    league distribution use estimated trips (TRIPS_PER_FTA x FTA); the
    featured game's own trips are counted exactly.
    """
    from nba_api.stats.endpoints import leaguegamelog
    lg = _call(lambda: leaguegamelog.LeagueGameLog(season=season),
               "leaguegamelog").get_data_frames()[0]
    rows = []
    for r in lg.to_dict("records"):
        fga, fta, tov, orb = r["FGA"], r["FTA"], r["TOV"], r["OREB"]
        poss = fga - orb + tov + 0.44 * fta
        tso = fga + round(TRIPS_PER_FTA * fta)
        rows.append({"tso": tso,
                     "ppo": round(r["PTS"] / tso, 3) if tso else None,
                     "tov_pct": round(100 * tov / poss, 1) if poss else None,
                     "ftr": round(fta / fga, 3) if fga else None,
                     "ts_pct": round(r["PTS"] / (2 * (fga + 0.44 * fta)), 3) if fga else None})
    # ORB% needs opponent DRB: pair rows by game
    by_game = {}
    for r, row in zip(lg.to_dict("records"), rows):
        by_game.setdefault(r["GAME_ID"], []).append((r, row))
    for pair in by_game.values():
        if len(pair) == 2:
            (r1, m1), (r2, m2) = pair
            m1["orb_pct"] = round(100 * r1["OREB"] / (r1["OREB"] + r2["DREB"]), 1)
            m2["orb_pct"] = round(100 * r2["OREB"] / (r2["OREB"] + r1["DREB"]), 1)

    def pct(values, v, higher_better=True):
        vals = [x for x in values if x is not None]
        if v is None or not vals:
            return None
        if higher_better:
            return round(100 * sum(1 for x in vals if x <= v) / len(vals))
        return round(100 * sum(1 for x in vals if x >= v) / len(vals))

    out = {}
    for key, hb in [("tso", True), ("ppo", True), ("tov_pct", False),
                    ("orb_pct", True), ("ftr", True), ("ts_pct", True)]:
        vals = [r[key] for r in rows]
        out[key] = {tri: pct(vals, featured[tri][key], hb) for tri in featured}
    return out, len(rows)


def _min_seconds(m):
    if m is None:
        return 0
    s = str(m)
    if ":" in s:
        try:
            mm, ss = s.split(":")
            return int(mm) * 60 + float(ss)
        except ValueError:
            return 0
    try:
        return float(s)
    except ValueError:
        return 0


def player_stats(rows, shots_by_tri, zone_avg):
    """Per-player framework numbers, keyed by team tricode.

    Box-score counting stats plus true shooting % and shot-location luck
    (actual FG points minus expected, from the same zone averages as the
    team shot quality). Players who did not play are dropped."""
    from collections import defaultdict
    shots_by_player = {}
    for tri, shots in shots_by_tri.items():
        d = defaultdict(list)
        for s in shots:
            d[str(s.get("PLAYER_ID"))].append(s)
        shots_by_player[tri] = d
    by_team = defaultdict(list)
    for r in rows:
        tri = r["teamTricode"]
        if _min_seconds(r.get("minutes")) <= 0:
            continue
        fga = int(r["fieldGoalsAttempted"])
        fta = int(r["freeThrowsAttempted"])
        pts = int(r["points"])
        ts = round(pts / (2 * (fga + 0.44 * fta)), 3) if (fga + 0.44 * fta) else None
        pshots = shots_by_player.get(tri, {}).get(str(r["personId"]), [])
        luck = sq = None
        if pshots:
            q = shot_quality(pshots, zone_avg)
            sq, luck = q["shot_quality"], q["luck_pts"]
        by_team[tri].append({
            "person_id": int(r["personId"]),
            "name": f"{r['firstName']} {r['familyName']}",
            "minutes": str(r["minutes"]),
            "pts": pts, "fga": fga, "fgm": int(r["fieldGoalsMade"]),
            "fta": fta, "ftm": int(r["freeThrowsMade"]),
            "orb": int(r["reboundsOffensive"]),
            "drb": int(r["reboundsDefensive"]),
            "ast": int(r["assists"]), "stl": int(r["steals"]),
            "blk": int(r["blocks"]), "tov": int(r["turnovers"]),
            "pf": int(r["foulsPersonal"]),
            "plus_minus": int(r["plusMinusPoints"]),
            "ts_pct": ts, "shot_quality": sq, "luck_pts": luck,
        })
    for tri in by_team:
        by_team[tri].sort(key=lambda p: (-p["pts"], p["name"]))
    return dict(by_team)


def compute_game(game_id, matchup, date, zone_avg, season):
    """Full framework output for one game, keyed by team tricode."""
    teams, pbp, shots, player_rows = fetch_game(game_id)
    home = None
    # Home team: the tricode in the matchup before "vs." (home) else after "@"
    if " vs. " in matchup:
        home = matchup.split(" vs. ")[0]
    else:
        home = matchup.split(" @ ")[1]
    away = next(t for t in teams if t != home)
    trips = count_trips(pbp)
    m = {t: team_metrics(b, trips.get(t, 0),
                         teams[away if t == home else home]["reboundsDefensive"])
         for t, b in teams.items()}
    sq = {t: shot_quality(shots[t], zone_avg) for t in teams}
    for t in teams:
        sq[t]["luck_per_opp"] = round(sq[t]["luck_pts"] / m[t]["tso"], 3)
    pctls, league_n = league_percentiles(season, m)
    quarters = quarter_splits(pbp, home, away)
    runs, series = detect_runs(pbp, home, away)
    return {
        "game_id": game_id, "date": date, "matchup": matchup,
        "home": home, "away": away,
        "teams": m, "shot_quality": sq, "league_pctl": pctls,
        "league_n": league_n, "quarters": {str(k): v for k, v in quarters.items()},
        "runs": runs, "diff_series": series,
        "final_diff": series[-1][1] if series else 0,
        "players": player_stats(player_rows, shots, zone_avg),
    }
