"""Build the Jazz postgame site.

State lives on the deployed site itself (site/data/*.json), so the scheduled
job needs no repo write access: it downloads the live data files, computes
only the games that are missing, rebuilds every page, and deploys.

Usage:
    python run.py [--out site] [--live-index URL] [--game-id ID] [--season S]
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pipeline import pipeline, site as site_mod  # noqa: E402

ROOT = Path(__file__).parent


def load_live(out, live_index_url):
    """Mirror the deployed data files into out/ so only new games are built."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "data").mkdir(exist_ok=True)
    try:
        with urllib.request.urlopen(live_index_url, timeout=30) as resp:
            index = json.load(resp)
    except Exception as exc:  # noqa: BLE001 - first deploy has no live index
        print(f"no live index ({exc}); building from scratch")
        return {}
    base = live_index_url.rsplit("/", 1)[0]
    games = {}
    for entry in index:
        gid = entry["game_id"]
        try:
            with urllib.request.urlopen(f"{base}/{gid}.json", timeout=30) as resp:
                games[gid] = json.load(resp)
            (out / "data" / f"{gid}.json").write_text(json.dumps(games[gid]))
        except Exception as exc:  # noqa: BLE001 - keep going with the rest
            print(f"could not fetch live data for {gid}: {exc}")
    return games


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--live-index", default=None,
                    help="URL of the deployed data/index.json")
    ap.add_argument("--game-id", default=None, help="Force-build one game")
    ap.add_argument("--season", default=None)
    args = ap.parse_args()

    out = Path(args.out)
    zone_avg = json.loads((ROOT / "data" / "zone_avg_2025_26.json").read_text())
    season = args.season or pipeline.current_season()
    print("season:", season)

    existing = {}
    if (out / "data").exists():
        for f in (out / "data").glob("*.json"):
            if f.name == "index.json":
                continue
            existing[f.stem] = json.loads(f.read_text())
    elif args.live_index:
        existing = load_live(out, args.live_index)
    print(f"existing games: {len(existing)}")

    if args.game_id:
        finals = None
        for g in pipeline.jazz_finals(season):
            if g["game_id"] == args.game_id:
                finals = [g]
        if finals is None:
            raise SystemExit(f"game {args.game_id} is not a completed Jazz game this season")
    else:
        finals = pipeline.jazz_finals(season)
    print(f"finals this season: {len(finals)}")

    built = 0
    for g in finals:
        gid = g["game_id"]
        if gid in existing and not args.game_id:
            continue
        print(f"computing {gid} ({g['matchup']}) ...")
        data = pipeline.compute_game(gid, g["matchup"], g["date"], zone_avg, season)
        existing[gid] = data
        (out / "data").mkdir(parents=True, exist_ok=True)
        (out / "data" / f"{gid}.json").write_text(json.dumps(data, indent=1))
        built += 1
    print(f"new games computed: {built}")

    games = sorted(existing.values(), key=lambda d: d["date"], reverse=True)
    (out / "games").mkdir(parents=True, exist_ok=True)
    for g in games:
        others = [o for o in games if o["game_id"] != g["game_id"]]
        (out / "games" / f"{g['game_id']}.html").write_text(
            site_mod.build_game_page(g, others))
        site_mod.build_hero(g, str(out / f"hero-{g['game_id']}.png"))
    (out / "index.html").write_text(site_mod.build_index(games))
    (out / "season.html").write_text(site_mod.build_season(games))
    index = [{"game_id": g["game_id"], "date": g["date"], "matchup": g["matchup"]}
             for g in games]
    (out / "data" / "index.json").write_text(json.dumps(index, indent=1))
    print(f"site written to {out} ({len(games)} games)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
