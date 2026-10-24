"""Site builder: game dashboard pages, index page, hero graphics.

Palette: Jazz Mountain Basketball — Mountain Purple #300370,
Midnight Black #0A0614, Sky Blue #79A3DC.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TEAM_NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}


SITE_URL = "https://jazz-postgame.vercel.app"

MOBILE_CSS = """
@media (max-width: 640px) {
  .wrap { padding: 20px 12px 40px; }
  h1 { font-size: 26px; }
  .story { font-size: 17px; padding: 14px; }
  table { display: block; overflow-x: auto; font-size: 14px; }
  th, td { padding: 7px; }
  td.num { font-size: 16px; }
  .bar { width: 48px; }
  .tabs button { padding: 8px 12px; font-size: 14px; }
}
"""


def _name(tri):
    return TEAM_NAMES.get(tri, tri)


def _opp(data):
    """The opponent's tricode (the team that is not Utah)."""
    return next(t for t in data["teams"] if t != "UTA")


def _fmt(v, spec="{}"):
    return spec.format(v) if v is not None else "—"


def _story(data):
    """One-line game story from the framework numbers (Jazz perspective)."""
    u, n = data["teams"]["UTA"], data["teams"][_opp(data)]
    opp = _opp(data)
    parts = []
    if abs(u["ppo"] - n["ppo"]) <= 0.01:
        parts.append(f"efficiency was a tie — both teams scored about "
                     f"{(u['ppo'] + n['ppo']) / 2:.2f} points per opportunity")
    elif u["ppo"] > n["ppo"]:
        parts.append(f"Utah outscored {_name(opp)} {u['ppo']} to {n['ppo']} "
                     f"per opportunity")
    else:
        parts.append(f"{_name(opp)} outscored Utah {n['ppo']} to {u['ppo']} "
                     f"per opportunity")
    if u["tso"] != n["tso"]:
        more = "Utah" if u["tso"] > n["tso"] else _name(opp)
        parts.append(f"{more} got up {abs(u['tso'] - n['tso'])} more "
                     f"opportunit{'y' if abs(u['tso'] - n['tso']) == 1 else 'ies'} "
                     f"({u['tso']} to {n['tso']})")
    else:
        parts.append(f"opportunities were even ({u['tso']} each)")
    if u["ftm"] != n["ftm"]:
        more = "Utah" if u["ftm"] > n["ftm"] else _name(opp)
        parts.append(f"{more} made {abs(u['ftm'] - n['ftm'])} more free throws "
                     f"({u['ftm']} to {n['ftm']})")
    return "The story in one line: " + "; ".join(parts) + "."


def _quarter_notes(data):
    """One line per quarter: score + biggest driver gap."""
    opp = _opp(data)
    notes = []
    for q in sorted(data["quarters"], key=int):
        qq = data["quarters"][q]
        u, n = qq["UTA"], qq[opp]
        winner = "Utah" if u["pts"] > n["pts"] else (_name(opp) if n["pts"] > u["pts"] else "Neither team")
        line = f"Q{q}: {winner} {max(u['pts'], n['pts'])}–{min(u['pts'], n['pts'])}."
        gaps = []
        if abs(u["orb_pct"] - n["orb_pct"]) >= 8:
            t = "Utah" if u["orb_pct"] > n["orb_pct"] else _name(opp)
            gaps.append(f"{t}'s {max(u['orb_pct'], n['orb_pct'])}% offensive rebounding")
        if abs(u["tov_pct"] - n["tov_pct"]) >= 8:
            t = "Utah" if u["tov_pct"] < n["tov_pct"] else _name(opp)
            gaps.append(f"{t} took care of the ball ({min(u['tov_pct'], n['tov_pct'])}% turnovers)")
        if abs(u["ftr"] - n["ftr"]) >= 0.2:
            t = "Utah" if u["ftr"] > n["ftr"] else _name(opp)
            gaps.append(f"{t} lived at the line ({max(u['fta'], n['fta'])} attempts)")
        if gaps:
            line += " Behind " + "; ".join(gaps) + "."
        notes.append(line)
    return notes


def _diff_svg(data):
    """Point-differential chart, always from Utah's perspective."""
    flip = -1 if data["home"] != "UTA" else 1
    series = [[e, flip * d] for e, d in data["diff_series"]]
    W, H, PL, PR, PT, PB = 800, 300, 46, 16, 18, 30
    diffs = [d for _, d in series]
    dmin, dmax = min(min(diffs), 0) - 3, max(max(diffs), 0) + 3

    def X(e):
        return PL + (e / 48) * (W - PL - PR)

    def Y(d):
        return PT + (dmax - d) / (dmax - dmin) * (H - PT - PB)

    pts = " ".join(f"{X(e):.1f},{Y(d):.1f}" for e, d in series)
    spans, markers = "", ""
    for i, run in enumerate(data["runs"], 1):
        x0, x1 = X(run["start_elapsed"]), X(run["end_elapsed"])
        color = "#79A3DC" if run["team"] == "UTA" else "#8B5CF6"
        spans += (f'<rect x="{x0:.1f}" y="{PT}" width="{max(x1 - x0, 6):.1f}" '
                  f'height="{H - PT - PB}" fill="{color}" opacity="0.13"/>')
        mx, my = X(run["end_elapsed"]), Y(flip * run["end_diff"])
        markers += (f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="13" fill="{color}"/>'
                    f'<text x="{mx:.1f}" y="{my + 4.5:.1f}" text-anchor="middle" '
                    f'font-size="13" font-weight="bold" fill="#0A0614">{i}</text>')
    return f"""<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg"
  font-family="-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif">
  <line x1="{PL}" y1="{Y(0):.1f}" x2="{W - PR}" y2="{Y(0):.1f}" stroke="#5B4A8A" stroke-width="1"/>
  {spans}
  <polyline points="{pts}" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linejoin="round"/>
  {markers}
  <text x="{PL}" y="{H - 8}" font-size="12" fill="#B7A9D9">Tip-off</text>
  <text x="{X(12):.0f}" y="{H - 8}" font-size="12" fill="#B7A9D9" text-anchor="middle">End Q1</text>
  <text x="{X(24):.0f}" y="{H - 8}" font-size="12" fill="#B7A9D9" text-anchor="middle">Half</text>
  <text x="{X(36):.0f}" y="{H - 8}" font-size="12" fill="#B7A9D9" text-anchor="middle">End Q3</text>
  <text x="{W - PR}" y="{H - 8}" font-size="12" fill="#B7A9D9" text-anchor="end">Final</text>
  <text x="{PL}" y="{PT - 5}" font-size="12" fill="#B7A9D9">Jazz lead ↑</text>
  <text x="{PL}" y="{H - PB + 18}" font-size="12" fill="#B7A9D9">Opponent lead ↓</text>
</svg>"""


def build_game_page(data, other_games):
    """Full dashboard HTML for one game. other_games: data dicts of the
    Jazz's other games this season (for the vs-own-average table)."""
    opp = _opp(data)
    u, n = data["teams"]["UTA"], data["teams"][opp]
    sq_u, sq_n = data["shot_quality"]["UTA"], data["shot_quality"][opp]
    P = data["league_pctl"]
    home_tri = data["home"]
    away_tri = next(t for t in data["teams"] if t != home_tri)
    opp_name = _name(opp)
    title = (f"{_name(home_tri)} {data['teams'][home_tri]['pts']}, "
             f"{_name(away_tri)} {data['teams'][away_tri]['pts']}")

    def bar(p):
        if p is None:
            return ""
        suffix = "th" if 11 <= p % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(p % 10, "th")
        return (f'<div class="bar"><div class="fill" style="width:{p}%"></div></div>'
                f'<span class="pct">{p}{suffix}</span>')

    def srow(label, uu, nn, pu=None, pn=None, note=""):
        cells = f'<td class="lbl">{label}</td><td class="num">{uu}</td><td class="num">{nn}</td>'
        cells += f'<td>{bar(pu)}</td><td>{bar(pn)}</td>' if pu is not None else '<td></td><td></td>'
        if note:
            cells += f'<td class="note">{note}</td>'
        return f"<tr>{cells}</tr>"

    qblocks = ""
    for q in sorted(data["quarters"], key=int):
        qq = data["quarters"][q]
        qu, qn = qq["UTA"], qq[opp]
        rows = ""
        for lbl, key, fmt in [
                ("Points", "pts", "{}"), ("Shot opportunities", "tso", "{}"),
                ("Points per opportunity", "ppo", "{:.3f}"),
                ("Turnover %", "tov_pct", "{}%"), ("Offensive rebound %", "orb_pct", "{}%"),
                ("Free-throw rate", "ftr", "{:.3f}"), ("True shooting %", "ts_pct", "{:.3f}")]:
            rows += (f'<tr><td class="lbl">{lbl}</td>'
                     f'<td class="num">{_fmt(qu[key], fmt)}</td>'
                     f'<td class="num">{_fmt(qn[key], fmt)}</td></tr>')
        qblocks += f"""<div class="qcard"><h3>Quarter {q} — Utah {qu["pts"]}, {opp_name} {qn["pts"]}</h3>
  <table><tr><th></th><th>Utah</th><th>{opp_name}</th></tr>{rows}</table></div>"""

    run_cards = ""
    for i, run in enumerate(data["runs"], 1):
        team = "Jazz" if run["team"] == "UTA" else opp_name
        color = "#79A3DC" if run["team"] == "UTA" else "#8B5CF6"
        if run["team"] == "UTA":
            sc = f"Jazz {run['home_pts'] if data['home'] == 'UTA' else run['away_pts']}–{run['away_pts'] if data['home'] == 'UTA' else run['home_pts']}"
        else:
            sc = f"{opp_name} {run['away_pts'] if data['home'] == 'UTA' else run['home_pts']}–{run['home_pts'] if data['home'] == 'UTA' else run['away_pts']}"
        drivers = "; ".join(run["drivers"]) if run["drivers"] else "steady scoring"
        run_cards += f"""<div class="runcard"><span class="dot" style="background:{color}">{i}</span>
  <div><b>{team} run, {sc}</b> · {run["start"]} → {run["end"]}
  ({run["duration_min"]} min of game time)<br>
  <span class="mut">Fueled by: {drivers}.</span></div></div>"""

    # Own-season comparison: Jazz averages across other games
    own_section = ""
    if other_games:
        keys = ["tso", "ppo", "orb_pct", "tov_pct", "ts_pct"]
        avg = {k: round(sum(g["teams"]["UTA"][k] for g in other_games) / len(other_games), 3)
               for k in keys}
        rows = ""
        for lbl, key in [("Total shot opportunities", "tso"),
                         ("Points per opportunity", "ppo"),
                         ("Offensive rebound %", "orb_pct"),
                         ("Turnover %", "tov_pct"),
                         ("True shooting %", "ts_pct")]:
            rows += (f'<tr><td class="lbl">{lbl}</td><td class="num">{u[key]}</td>'
                     f'<td class="num">{avg[key]}</td></tr>')
        own_section = f"""<h2>Against Utah's own season so far</h2>
<table><tr><th></th><th>This game</th><th>Season avg (other {len(other_games)} game{'s' if len(other_games) != 1 else ''})</th></tr>
{rows}</table>"""

    # Player drivers: Jazz table + opponent leaders line
    players_section = ""
    pj = data.get("players", {}).get("UTA", [])
    po = data.get("players", {}).get(opp, [])
    if pj:
        def _luck_str(p):
            return f"{p['luck_pts']:+.1f}" if p["luck_pts"] is not None else "—"

        def _ts_str(p):
            return f"{p['ts_pct']:.3f}" if p["ts_pct"] is not None else "—"

        prows = ""
        for p in pj:
            prows += (f'<tr><td class="lbl">{p["name"]}</td><td>{p["minutes"]}</td>'
                      f'<td class="num">{p["pts"]}</td><td class="num">{p["orb"]}</td>'
                      f'<td class="num">{p["stl"]}</td><td class="num">{p["tov"]}</td>'
                      f'<td class="num">{p["fta"]}</td><td class="num">{_ts_str(p)}</td>'
                      f'<td class="num">{_luck_str(p)}</td></tr>')
        lead_bits = []
        top_orb = max(pj, key=lambda p: p["orb"])
        top_stl = max(pj, key=lambda p: p["stl"])
        if top_orb["orb"] > 0:
            lead_bits.append(f"{top_orb['name']} ({top_orb['orb']} offensive board{'s' if top_orb['orb'] != 1 else ''})")
        if top_stl["stl"] > 0:
            lead_bits.append(f"{top_stl['name']} ({top_stl['stl']} steal{'s' if top_stl['stl'] != 1 else ''})")
        lead = (f'<p class="note">Jazz chance-creators: {"; ".join(lead_bits)}.</p>'
                if lead_bits else "")
        opp_line = ""
        if po:
            so = max(po, key=lambda p: p["pts"])
            oo = max(po, key=lambda p: p["orb"])
            st = max(po, key=lambda p: p["stl"])
            opp_line = (f'<p class="note">{opp_name} leaders: {so["name"]} ({so["pts"]} pts) · '
                        f'{oo["name"]} ({oo["orb"]} offensive board{"s" if oo["orb"] != 1 else ""}) · '
                        f'{st["name"]} ({st["stl"]} steal{"s" if st["stl"] != 1 else ""}).</p>')
        players_section = f"""<h2>Player drivers</h2>
{lead}
<table><tr><th>Utah player</th><th>MIN</th><th>PTS</th><th>ORB</th><th>STL</th>
<th>TOV</th><th>FTA</th><th>TS%</th><th>Shot-making</th></tr>
{prows}</table>
<p class="note">Shot-making is field-goal points above expected from shot locations; with only a
handful of attempts per player, one make swings it by 2–3 points.</p>
{opp_line}"""
    og_desc = _story(data).replace('"', "&quot;")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Jazz Postgame</title>
<meta property="og:title" content="{title} — Jazz Postgame">
<meta property="og:description" content="{og_desc}">
<meta property="og:image" content="{SITE_URL}/hero-{data['game_id']}.png">
<meta property="og:url" content="{SITE_URL}/games/{data['game_id']}.html">
<meta property="og:type" content="article">
<meta name="twitter:card" content="summary_large_image">
<style>
body {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
  margin: 0; background: #0A0614; color: #F2EFFA; }}
.wrap {{ max-width: 860px; margin: 0 auto; padding: 28px 20px 60px; }}
a {{ color: #79A3DC; }}
h1 {{ font-size: 34px; margin: 0 0 4px; }}
.sub {{ color: #B7A9D9; margin: 0 0 18px; }}
.tabs {{ display: flex; gap: 8px; margin: 0 0 22px; }}
.tabs button {{ background: #1B1035; color: #F2EFFA; border: 1px solid #3A2A6B;
  padding: 10px 18px; border-radius: 8px; font-size: 15px; cursor: pointer; }}
.tabs button.active {{ background: #300370; border-color: #79A3DC; font-weight: 700; }}
.tab {{ display: none; }} .tab.active {{ display: block; }}
.story {{ background: #1B1035; border-left: 5px solid #79A3DC; padding: 16px 18px;
  font-size: 19px; line-height: 1.5; border-radius: 0 8px 8px 0; }}
.story b {{ color: #79A3DC; }}
h2 {{ font-size: 20px; margin: 30px 0 10px; color: #79A3DC; letter-spacing: .3px; }}
h3 {{ font-size: 17px; margin: 0 0 8px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 16px; }}
th {{ text-align: left; color: #B7A9D9; font-size: 13px; text-transform: uppercase;
  letter-spacing: .5px; padding: 8px 10px; border-bottom: 1px solid #3A2A6B; }}
td {{ padding: 10px; border-bottom: 1px solid #241645; vertical-align: middle; }}
td.num {{ font-weight: 700; font-size: 19px; white-space: nowrap; color: #79A3DC; }}
td.lbl {{ font-weight: 600; }}
.bar {{ display: inline-block; width: 90px; height: 9px; background: #241645;
  border-radius: 5px; vertical-align: middle; overflow: hidden; }}
.fill {{ height: 100%; background: #79A3DC; border-radius: 5px; }}
.pct {{ color: #B7A9D9; font-size: 13px; margin-left: 6px; }}
.note {{ color: #B7A9D9; font-size: 14px; }}
.foot {{ color: #B7A9D9; font-size: 13.5px; line-height: 1.6; margin-top: 26px; }}
.foot b {{ color: #F2EFFA; }}
.qcard {{ background: #120A24; border: 1px solid #3A2A6B; border-radius: 10px;
  padding: 16px 18px; margin: 0 0 16px; }}
.qcard td.num {{ color: #F2EFFA; }}
.runcard {{ display: flex; gap: 12px; background: #120A24; border: 1px solid #3A2A6B;
  border-radius: 10px; padding: 14px 16px; margin: 0 0 12px; line-height: 1.5; }}
.dot {{ flex: 0 0 26px; height: 26px; border-radius: 50%; color: #0A0614;
  font-weight: 800; font-size: 14px; display: flex; align-items: center;
  justify-content: center; }}
.mut {{ color: #B7A9D9; }}
.chartbox {{ background: #120A24; border: 1px solid #3A2A6B; border-radius: 10px;
  padding: 12px 8px 4px; }}
{MOBILE_CSS}
</style>
<script>
function showTab(id, btn) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}}
</script></head><body><div class="wrap">
<p><a href="../index.html">← All games</a> · <a href="../season.html">Season so far</a></p>
<h1>{title}</h1>
<p class="sub">{data["date"]} · Jazz postgame dashboard</p>
<div class="tabs">
  <button class="active" onclick="showTab('summary', this)">Game summary</button>
  <button onclick="showTab('quarters', this)">Quarters &amp; runs</button>
</div>

<div id="summary" class="tab active">
<div class="story">{_story(data)}</div>

<h2>The two headline numbers</h2>
<table><tr><th></th><th>Utah</th><th>{opp_name}</th>
<th>UTA league pct</th><th>{opp} league pct</th></tr>
{srow("Total shot opportunities", u["tso"], n["tso"], P["tso"]["UTA"], P["tso"][opp],
     f"FGA + free-throw trips ({u['fga']} + {u['trips']} vs {n['fga']} + {n['trips']})")}
{srow("Points per opportunity", u["ppo"], n["ppo"], P["ppo"]["UTA"], P["ppo"][opp],
     "Points ÷ shot opportunities")}
</table>

<h2>Why the opportunities split that way</h2>
<table><tr><th></th><th>Utah</th><th>{opp_name}</th>
<th>UTA league pct</th><th>{opp} league pct</th></tr>
{srow("Turnover %", f"{u['tov_pct']}%", f"{n['tov_pct']}%", P["tov_pct"]["UTA"], P["tov_pct"][opp],
     "Lower is better")}
{srow("Offensive rebound %", f"{u['orb_pct']}%", f"{n['orb_pct']}%", P["orb_pct"]["UTA"], P["orb_pct"][opp],
     f"{u['orb']} offensive boards vs {n['orb']}")}
{srow("Free-throw rate", u["ftr"], n["ftr"], P["ftr"]["UTA"], P["ftr"][opp],
     f"FTA ÷ FGA ({u['fta']} FTA vs {n['fta']})")}
</table>

<h2>Why the points per opportunity landed there</h2>
<table><tr><th></th><th>Utah</th><th>{opp_name}</th>
<th>UTA league pct</th><th>{opp} league pct</th></tr>
{srow("True shooting %", u["ts_pct"], n["ts_pct"], P["ts_pct"]["UTA"], P["ts_pct"][opp], "")}
{srow("Shot quality", sq_u["shot_quality"], sq_n["shot_quality"], None, None,
     "Expected points per field-goal attempt from shot locations")}
{srow("Shot-making", f"+{sq_u['luck_pts']} pts" if sq_u["luck_pts"] >= 0 else f"{sq_u['luck_pts']} pts",
     f"+{sq_n['luck_pts']} pts" if sq_n["luck_pts"] >= 0 else f"{sq_n['luck_pts']} pts", None, None,
     f"Actual FG points minus expected ({sq_u['act_fg_pts']} vs {sq_u['exp_pts']} expected; {sq_n['act_fg_pts']} vs {sq_n['exp_pts']})")}
</table>
{players_section}
{own_section}
<p class="foot"><b>How to read the percentiles:</b> each game's value ranked against all
{data["league_n"]} team-games played league-wide so far this season.
For turnover %, the percentile is flipped — a lower number means fewer teams
turned it over more. Early in the season these percentiles move a lot.
<b>Shot quality</b> uses last season's league-average make rates by shot zone.
<b>Shot-making</b> is field-goal points above expected from shot locations. Free-throw trips are counted from the
official play-by-play, not estimated. League shot-opportunity percentiles use
estimated trips for other teams (0.556 trips per FTA, measured across early-season
games); this game's own trips are counted exactly.</p>
</div>

<div id="quarters" class="tab">
<h2>Quarter by quarter</h2>
<p class="foot" style="margin-top:0">Same framework, per quarter. A quarter is only
about 25 opportunities, so one hot or cold stretch moves these numbers a lot.</p>
{qblocks}
<p class="foot">{' '.join(_quarter_notes(data))}</p>

<h2>Game flow: point differential and the runs</h2>
<p class="foot" style="margin-top:0">Jazz lead above the line, opponent lead below.
Shaded spans are runs: stretches where the differential swung at least 10 points
one way. Numbers match the cards below.</p>
<div class="chartbox">{_diff_svg(data)}</div>
<h2 style="margin-top:24px">The runs, explained</h2>
{run_cards}
<p class="foot"><b>How runs are detected:</b> the differential is tracked after every
scoring play; a run is any stretch where it moves at least 10 points in one
team's favor from its previous extreme. The "fueled by" drivers are counted
from the play-by-play inside that exact window.</p>
</div>
</div></body></html>"""


def build_index(games):
    """games: list of game data dicts, newest first."""
    wins = sum(1 for g in games
               if g["teams"]["UTA"]["pts"] > g["teams"][next(t for t in g["teams"] if t != "UTA")]["pts"])
    record = f"{wins}–{len(games) - wins}" if games else "0–0"
    through = games[0]["date"] if games else ""
    rows = ""
    for g in games:
        opp = next(t for t in g["teams"] if t != "UTA")
        u, n = g["teams"]["UTA"], g["teams"][opp]
        home_tri = g["home"]
        away_tri = next(t for t in g["teams"] if t != home_tri)
        title = (f"{_name(home_tri)} {g['teams'][home_tri]['pts']}, "
                 f"{_name(away_tri)} {g['teams'][away_tri]['pts']}")
        tso_diff = u["tso"] - n["tso"]
        rows += (f'<tr><td>{g["date"]}</td>'
                 f'<td><a href="games/{g["game_id"]}.html"><b>{title}</b></a></td>'
                 f'<td class="num">{tso_diff:+d}</td>'
                 f'<td class="num">{u["ppo"]} – {n["ppo"]}</td>'
                 f'<td><a href="hero-{g["game_id"]}.png">Graphic</a></td></tr>')
    hero_latest = f"{SITE_URL}/hero-{games[0]['game_id']}.png" if games else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jazz Postgame — Shot Opportunities × Points Per Opportunity</title>
<meta property="og:title" content="Jazz Postgame — Shot Opportunities × Points Per Opportunity">
<meta property="og:description" content="Every Utah Jazz game broken down the same way: total shot opportunities and points per opportunity, with the numbers that explain both.">
<meta property="og:image" content="{hero_latest}">
<meta property="og:url" content="{SITE_URL}/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<style>
body {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
  margin: 0; background: #0A0614; color: #F2EFFA; }}
.wrap {{ max-width: 860px; margin: 0 auto; padding: 28px 20px 60px; }}
a {{ color: #79A3DC; text-decoration: none; }}
h1 {{ font-size: 32px; margin: 0 0 6px; }}
.sub {{ color: #B7A9D9; margin: 0 0 24px; line-height: 1.5; }}
.strip {{ background: #1B1035; border: 1px solid #3A2A6B; border-radius: 10px;
  padding: 14px 18px; margin: 0 0 24px; line-height: 1.6; }}
.strip b {{ color: #F2EFFA; }}
table {{ width: 100%; border-collapse: collapse; font-size: 16px; }}
th {{ text-align: left; color: #B7A9D9; font-size: 13px; text-transform: uppercase;
  letter-spacing: .5px; padding: 8px 10px; border-bottom: 1px solid #3A2A6B; }}
td {{ padding: 10px; border-bottom: 1px solid #241645; vertical-align: middle; }}
td.num {{ font-weight: 700; font-size: 17px; white-space: nowrap; color: #79A3DC; }}
.mut {{ color: #B7A9D9; font-size: 14.5px; }}
{MOBILE_CSS}
</style></head><body><div class="wrap">
<h1>Jazz Postgame</h1>
<p class="sub">Every game broken down the same way: how many shots each team got up,
and how well they did with them — total shot opportunities (field-goal attempts
+ free-throw trips) and points per opportunity, with the numbers that explain both.</p>
<div class="strip"><b>Record: {record}</b> · Through {through} · <a href="season.html">Season so far →</a></div>
<table><tr><th>Date</th><th>Game</th><th>TSO diff</th><th>PPO (UTA – opp)</th><th>Hero</th></tr>
{rows}</table>
<p class="mut">TSO diff is Utah's total shot opportunities minus the opponent's. PPO is points per opportunity.</p>
</div></body></html>"""


def _suffix(p):
    return "th" if 11 <= p % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(p % 10, "th")


def _short_date(date_str):
    return date_str.split(",")[0].title()


def _tso_diff_svg(chron):
    """Bars: Utah's shot-opportunity differential per game, chronological."""
    W, H, PL, PR, PT, PB = 800, 280, 46, 16, 20, 34
    vals = []
    for g in chron:
        opp = next(t for t in g["teams"] if t != "UTA")
        vals.append(g["teams"]["UTA"]["tso"] - g["teams"][opp]["tso"])
    lim = max(max(abs(v) for v in vals), 1) + 3
    plot_w, plot_h = W - PL - PR, H - PT - PB
    y0 = PT + plot_h / 2

    def Y(v):
        return y0 - (v / lim) * (plot_h / 2)

    n = len(vals)
    step = plot_w / max(n, 1)
    bars, labels = "", ""
    for i, (g, v) in enumerate(zip(chron, vals)):
        x = PL + i * step + step * 0.22
        w = step * 0.56
        color = "#79A3DC" if v >= 0 else "#8B5CF6"
        y_top, h = (Y(v), y0 - Y(v)) if v >= 0 else (y0, Y(v) - y0)
        opp = next(t for t in g["teams"] if t != "UTA")
        bars += (f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{w:.1f}" height="{max(h, 2):.1f}" '
                 f'fill="{color}" rx="3"><title>{_short_date(g["date"])} vs {opp}: {v:+d}</title></rect>')
        labels += (f'<text x="{x + w / 2:.1f}" y="{H - 10}" font-size="12" fill="#B7A9D9" '
                   f'text-anchor="middle">{_short_date(g["date"])}</text>')
    return f"""<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg"
  font-family="-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif">
  <line x1="{PL}" y1="{y0:.1f}" x2="{W - PR}" y2="{y0:.1f}" stroke="#5B4A8A" stroke-width="1"/>
  {bars}
  {labels}
  <text x="{PL}" y="{PT - 6}" font-size="12" fill="#B7A9D9">More chances than opponent ↑</text>
  <text x="{PL}" y="{H - PB + 26}" font-size="12" fill="#B7A9D9">Fewer chances ↓</text>
</svg>"""


def _ppo_svg(chron):
    """Lines: points per opportunity, Utah vs opponent, chronological."""
    W, H, PL, PR, PT, PB = 800, 280, 46, 16, 20, 34
    jazz, opps = [], []
    for g in chron:
        opp = next(t for t in g["teams"] if t != "UTA")
        jazz.append(g["teams"]["UTA"]["ppo"])
        opps.append(g["teams"][opp]["ppo"])
    lo = min(min(jazz), min(opps)) - 0.03
    hi = max(max(jazz), max(opps)) + 0.03
    plot_w, plot_h = W - PL - PR, H - PT - PB
    n = len(jazz)

    def X(i):
        return PL + (i / max(n - 1, 1)) * plot_w if n > 1 else PL + plot_w / 2

    def Y(v):
        return PT + (hi - v) / (hi - lo) * plot_h

    def line(series, color):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(series))
        dots = "".join(
            f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="5" fill="{color}">'
            f'<title>{_short_date(chron[i]["date"])}: {v}</title></circle>'
            for i, v in enumerate(series))
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>{dots}'

    labels = "".join(
        f'<text x="{X(i):.1f}" y="{H - 10}" font-size="12" fill="#B7A9D9" text-anchor="middle">'
        f'{_short_date(g["date"])}</text>' for i, g in enumerate(chron))
    return f"""<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg"
  font-family="-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif">
  {line(opps, "#8B5CF6")}
  {line(jazz, "#79A3DC")}
  {labels}
  <text x="{PL}" y="{PT - 6}" font-size="12" fill="#79A3DC">— Utah</text>
  <text x="{PL + 70}" y="{PT - 6}" font-size="12" fill="#8B5CF6">— Opponent</text>
</svg>"""


def build_season(games):
    """Season-so-far page: averages, trend charts, per-game log.
    games: list of game data dicts, newest first."""
    if not games:
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Season so far — Jazz Postgame</title></head><body><div class="wrap">
<p><a href="index.html">← All games</a></p><h1>Season so far</h1>
<p>No finished games yet.</p></div></body></html>"""
    chron = list(reversed(games))
    wins = 0
    for g in games:
        opp = next(t for t in g["teams"] if t != "UTA")
        if g["teams"]["UTA"]["pts"] > g["teams"][opp]["pts"]:
            wins += 1
    record = f"{wins}–{len(games) - wins}"
    avg_rows = ""
    for lbl, key, fmt in [("Total shot opportunities", "tso", "{}"),
                          ("Points per opportunity", "ppo", "{:.3f}"),
                          ("Turnover %", "tov_pct", "{}%"),
                          ("Offensive rebound %", "orb_pct", "{}%"),
                          ("Free-throw rate", "ftr", "{:.3f}"),
                          ("True shooting %", "ts_pct", "{:.3f}")]:
        avg = sum(g["teams"]["UTA"][key] for g in games) / len(games)
        pct = round(sum(g["league_pctl"][key]["UTA"] for g in games) / len(games))
        avg_rows += (f'<tr><td class="lbl">{lbl}</td><td class="num">{_fmt(avg, fmt)}</td>'
                     f'<td class="note">{pct}{_suffix(pct)} percentile on average</td></tr>')
    log_rows = ""
    for g in games:
        opp = next(t for t in g["teams"] if t != "UTA")
        u, n = g["teams"]["UTA"], g["teams"][opp]
        home_tri = g["home"]
        away_tri = next(t for t in g["teams"] if t != home_tri)
        title = (f"{_name(home_tri)} {g['teams'][home_tri]['pts']}, "
                 f"{_name(away_tri)} {g['teams'][away_tri]['pts']}")
        log_rows += (f'<tr><td>{g["date"]}</td>'
                     f'<td><a href="games/{g["game_id"]}.html"><b>{title}</b></a></td>'
                     f'<td class="num">{u["tso"] - n["tso"]:+d}</td>'
                     f'<td class="num">{u["ppo"]}</td><td class="num">{n["ppo"]}</td>'
                     f'<td class="num">{u["tov_pct"]}%</td><td class="num">{u["orb_pct"]}%</td></tr>')
    tot = {}
    for g in games:
        for p in g.get("players", {}).get("UTA", []):
            t = tot.setdefault(p["person_id"], {
                "name": p["name"], "gp": 0, "pts": 0, "orb": 0, "stl": 0,
                "fga": 0, "fta": 0, "luck": 0.0, "has_shots": False})
            t["gp"] += 1
            t["pts"] += p["pts"]
            t["orb"] += p["orb"]
            t["stl"] += p["stl"]
            t["fga"] += p["fga"]
            t["fta"] += p["fta"]
            if p["luck_pts"] is not None:
                t["luck"] += p["luck_pts"]
                t["has_shots"] = True
    srows = ""
    for t in sorted(tot.values(), key=lambda x: -x["pts"]):
        denom = 2 * (t["fga"] + 0.44 * t["fta"])
        ts = round(t["pts"] / denom, 3) if denom else None
        luck = f"{t['luck']:+.1f}" if t["has_shots"] else "—"
        srows += (f'<tr><td class="lbl">{t["name"]}</td><td>{t["gp"]}</td>'
                  f'<td class="num">{t["pts"]}</td><td class="num">{t["orb"]}</td>'
                  f'<td class="num">{t["stl"]}</td>'
                  f'<td class="num">{f"{ts:.3f}" if ts is not None else "—"}</td>'
                  f'<td class="num">{luck}</td></tr>')
    player_totals = f"""<h2>Jazz player totals</h2>
<table><tr><th>Player</th><th>GP</th><th>PTS</th><th>ORB</th><th>STL</th><th>TS%</th><th>Shot-making</th></tr>
{srows}</table>""" if srows else ""
    hero_latest = f"{SITE_URL}/hero-{games[0]['game_id']}.png"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Season so far — Jazz Postgame</title>
<meta property="og:title" content="Season so far — Jazz Postgame">
<meta property="og:description" content="Utah Jazz season averages and game-by-game trends in total shot opportunities and points per opportunity.">
<meta property="og:image" content="{hero_latest}">
<meta property="og:url" content="{SITE_URL}/season.html">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<style>
body {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
  margin: 0; background: #0A0614; color: #F2EFFA; }}
.wrap {{ max-width: 860px; margin: 0 auto; padding: 28px 20px 60px; }}
a {{ color: #79A3DC; text-decoration: none; }}
h1 {{ font-size: 32px; margin: 0 0 6px; }}
.sub {{ color: #B7A9D9; margin: 0 0 24px; line-height: 1.5; }}
h2 {{ font-size: 20px; margin: 30px 0 10px; color: #79A3DC; letter-spacing: .3px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 16px; }}
th {{ text-align: left; color: #B7A9D9; font-size: 13px; text-transform: uppercase;
  letter-spacing: .5px; padding: 8px 10px; border-bottom: 1px solid #3A2A6B; }}
td {{ padding: 10px; border-bottom: 1px solid #241645; vertical-align: middle; }}
td.num {{ font-weight: 700; font-size: 17px; white-space: nowrap; color: #79A3DC; }}
td.lbl {{ font-weight: 600; }}
.note {{ color: #B7A9D9; font-size: 14px; }}
.foot {{ color: #B7A9D9; font-size: 13.5px; line-height: 1.6; margin-top: 26px; }}
.chartbox {{ background: #120A24; border: 1px solid #3A2A6B; border-radius: 10px;
  padding: 12px 8px 4px; }}
{MOBILE_CSS}
</style></head><body><div class="wrap">
<p><a href="index.html">← All games</a></p>
<h1>Season so far</h1>
<p class="sub">Record: <b>{record}</b> · {len(games)} game{'s' if len(games) != 1 else ''} ·
Through {games[0]["date"]}</p>
<h2>Utah's season averages</h2>
<table><tr><th></th><th>Average</th><th>League context</th></tr>
{avg_rows}</table>
<h2>Shot-opportunity differential per game</h2>
<div class="chartbox">{_tso_diff_svg(chron)}</div>
<h2>Points per opportunity per game</h2>
<div class="chartbox">{_ppo_svg(chron)}</div>
<h2>Game log</h2>
<table><tr><th>Date</th><th>Game</th><th>TSO diff</th><th>UTA PPO</th><th>Opp PPO</th>
<th>UTA TOV%</th><th>UTA ORB%</th></tr>
{log_rows}</table>
{player_totals}
<p class="foot">Averages are across all games above. The percentile column averages each
game's league percentile rank, so it moves as the league sample grows — early in
the season it swings a lot. For turnover %, a lower percentile means fewer teams
turned it over more.</p>
</div></body></html>"""


def build_hero(data, path):
    """1080×1350 hero graphic, Mountain Basketball palette."""
    BG, PURPLE, SKY, WHITE, MUT, DIV = "#0A0614", "#300370", "#79A3DC", "#FFFFFF", "#B7A9D9", "#3A2A6B"
    opp = _opp(data)
    u, n = data["teams"]["UTA"], data["teams"][opp]
    sq_u, sq_n = data["shot_quality"]["UTA"], data["shot_quality"][opp]
    home = data["home"] == "UTA"
    jazz_won = u["pts"] > n["pts"]
    avg_ppo = (u["ppo"] + n["ppo"]) / 2
    avg_tso = (u["tso"] + n["tso"]) / 2
    vol_j = (u["tso"] - n["tso"]) * avg_ppo
    eff_j = (u["ppo"] - n["ppo"]) * avg_tso
    if abs(vol_j) >= abs(eff_j) and u["tso"] != n["tso"]:
        if jazz_won:
            d = u["tso"] - n["tso"]
            big = [f"Won by {d}", "opportunity." if d == 1 else "opportunities."]
        else:
            d = n["tso"] - u["tso"]
            big = [f"Lost by {d}", "opportunity." if d == 1 else "opportunities."]
        sub = ("Efficiency was dead even. " if abs(u["ppo"] - n["ppo"]) <= 0.01
               else f"Efficiency: {u['ppo']} vs {n['ppo']}. ")
        if u["tso"] > n["tso"]:
            sub += f"Utah got up {u['tso'] - n['tso']} more shot{'s' if u['tso'] - n['tso'] != 1 else ''}."
        elif n["tso"] > u["tso"]:
            sub += f"{opp} got up {n['tso'] - u['tso']} more shots."
        else:
            sub += "Opportunities were even."
    else:
        big = ["Won on", "efficiency."] if jazz_won else ["Lost on", "efficiency."]
        sub = f"{u['ppo']} vs {n['ppo']} points per opportunity."
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 108); ax.set_ylim(0, 135); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 108, 135, color=BG))
    ax.add_patch(plt.Rectangle((0, 126), 108, 9, color=PURPLE))
    ax.text(54, 130.5, "JAZZ POSTGAME", ha="center", va="center", fontsize=26,
            fontweight="bold", color=WHITE)
    if home:
        score = f"JAZZ  {u['pts']} — {n['pts']}  {opp}"
    else:
        score = f"{opp}  {n['pts']} — {u['pts']}  JAZZ"
    ax.text(54, 120.5, score, ha="center", fontsize=29, fontweight="bold", color=WHITE)
    ax.text(54, 115.5, f"{data['date']}  ·  {_name(opp)}", ha="center", fontsize=16, color=MUT)
    ax.text(54, 105.5, big[0], ha="center", fontsize=42, fontweight="bold", color=WHITE)
    ax.text(54, 98, big[1], ha="center", fontsize=42, fontweight="bold", color=SKY)
    ax.text(54, 91, sub, ha="center", fontsize=16.5, color=MUT)
    ax.text(54, 86.5, "All numbers: Utah — " + opp + " · jazz-postgame.vercel.app", ha="center", fontsize=13.5, color=MUT)
    ax.plot([8, 100], [82.5, 82.5], color=DIV, lw=1.5)

    def row(y, label, val, lab_fs=18):
        ax.text(8, y, label, fontsize=lab_fs, color=WHITE, fontweight="bold", va="center")
        ax.text(100, y, val, fontsize=20, color=SKY, fontweight="bold", va="center", ha="right")

    row(76.5, "Shot opportunities", f"{u['tso']} — {n['tso']}")
    row(68.5, "Points per opportunity", f"{u['ppo']} — {n['ppo']}")
    ax.plot([8, 100], [63, 63], color=DIV, lw=1.5)
    ax.text(8, 58, "WHY THE OPPORTUNITIES SPLIT THAT WAY", fontsize=14.5, color=SKY,
            fontweight="bold", va="center")
    row(52, "Offensive rebound %", f"{u['orb_pct']}% — {n['orb_pct']}%")
    row(44, "Turnover %", f"{u['tov_pct']}% — {n['tov_pct']}%")
    row(36, "Free-throw trips", f"{u['trips']} — {n['trips']}")
    ax.plot([8, 100], [31, 31], color=DIV, lw=1.5)
    ax.text(8, 26, "WHY THE EFFICIENCY LANDED THERE", fontsize=14.5, color=SKY,
            fontweight="bold", va="center")
    row(20, "True shooting %", f"{u['ts_pct']} — {n['ts_pct']}")
    row(12.5, "Shot quality (exp. pts / attempt)", f"{sq_u['shot_quality']} — {sq_n['shot_quality']}")
    luck = lambda s: f"+{s['luck_pts']}" if s["luck_pts"] >= 0 else f"{s['luck_pts']}"
    row(5, "Shot-making (pts above expected)", f"{luck(sq_u)} — {luck(sq_n)}")
    fig.savefig(path, dpi=100)
    plt.close(fig)
