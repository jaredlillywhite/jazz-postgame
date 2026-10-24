# Jazz Postgame

Every Utah Jazz game broken down the same way: **how many shots each team
got up, and how well they did with them.**

- **Total shot opportunities** = field-goal attempts + free-throw trips
  (trips counted from the official play-by-play, never estimated)
- **Points per opportunity** = points ÷ shot opportunities

Opportunities are explained by turnover %, offensive rebound %, and
free-throw rate. Efficiency is explained by shot quality (expected points per
attempt from shot locations, using last season's league-average make rates by
zone), true shooting %, and a shooting-luck measure (actual field-goal points
minus expected points from those shots' locations).

Each game page also shows percentiles against all team-games played
league-wide so far this season, the same numbers against Utah's own season
average, quarter-by-quarter splits, and a point-differential chart with
automatically detected and explained runs (any 10+ point swing, with the
offensive rebounds, forced turnovers, threes, and free throws inside it).

## How it runs

No server, no database. A scheduled GitHub Actions job checks for newly
finished Jazz games on game nights, computes the new games, rebuilds the
static site, and deploys it to GitHub Pages. State lives on the deployed site
itself (`data/*.json`), so the job needs no repo write access.

## Data

NBA Stats API via `nba_api` (V3 endpoints — the older V2 boxscore and
play-by-play endpoints no longer return data). The API is unofficial and
occasionally blocks cloud IPs; the pipeline retries, and a failed run simply
retries on the next schedule instead of publishing wrong numbers.

League shot-opportunity percentiles use estimated free-throw trips for other
teams (0.556 trips per free-throw attempt, measured across early-season
games); the featured game's own trips are always counted exactly.
