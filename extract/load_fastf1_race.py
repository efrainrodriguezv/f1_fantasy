"""
Extract FastF1 session data for one or many race weekends.

Usage:
    python extract/load_fastf1_race.py 2024 1            # one race weekend
    python extract/load_fastf1_race.py 2024              # full season
    python extract/load_fastf1_race.py 2024,2025         # multiple seasons
"""
import os
import sys
from pathlib import Path

import fastf1
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


# Session types we attempt for every weekend.
# FastF1 raises an exception for sessions that don't exist (e.g. sprint at a
# non-sprint weekend). We catch that per-session.
SESSION_TYPES = ["FP1", "FP2", "FP3", "Q", "SS", "S", "R"]


def get_engine():
    load_dotenv()
    user = os.environ["SUPABASE_USER"]
    password = os.environ["SUPABASE_PASSWORD"]
    host = os.environ["SUPABASE_HOST"]
    port = os.environ["SUPABASE_PORT"]
    db = os.environ["SUPABASE_DB"]
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def enable_cache():
    cache_dir = Path(__file__).parent.parent / ".fastf1_cache"
    cache_dir.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))


def load_session(year, round_number, session_type, engine, max_retries=5):
    """Pull one session's results with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            session = fastf1.get_session(year, round_number, session_type)
            session.load(laps=False, telemetry=False, weather=False)
            break
        except RateLimitExceededError:
            wait = 2 ** attempt * 60  # 60s, 120s, 240s, 480s, 960s
            print(f"  {session_type}: rate limited, sleeping {wait}s (attempt {attempt+1}/{max_retries})")
            time.sleep(wait)
    else:
        print(f"  {session_type}: gave up after {max_retries} retries")
        return

    results = session.results.copy()
    if results.empty:
        print(f"  {session_type}: empty")
        return

    results["season_year"] = year
    results["round_number"] = round_number
    results["session_type_code"] = session_type
    results["event_name"] = session.event["EventName"]
    results["session_start"] = session.date

    # Stringify object-typed columns to avoid pandas-to-sql type issues
    for col in results.columns:
        if results[col].dtype == "object":
            results[col] = results[col].astype(str)

    results.to_sql(
        "fastf1_session_results",
        engine,
        schema="raw",
        if_exists="append",
        index=False,
    )
    print(f"  {session_type}: {len(results)} rows")


def load_weekend(year, round_number, engine):
    print(f"=== {year} Round {round_number} ===")
    for session_type in SESSION_TYPES:
        try:
            load_session(year, round_number, session_type, engine)
        except Exception as e:
            # Most common reason: session doesn't exist for this weekend
            # (sprint at non-sprint weekend, FP3 at sprint weekend, etc.)
            print(f"  {session_type}: skipped ({type(e).__name__})")


def get_season_rounds(year):
    """Return list of round numbers for a given season."""
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return schedule["RoundNumber"].tolist()


def main():
    if len(sys.argv) < 2:
        print("Usage: python load_fastf1_race.py <year>[,<year>] [<round>]")
        sys.exit(1)

    # Parse arg 1: one or more years, comma-separated
    years = [int(y) for y in sys.argv[1].split(",")]

    # Parse arg 2 (optional): single round number
    target_round = int(sys.argv[2]) if len(sys.argv) >= 3 else None

    enable_cache()
    engine = get_engine()

    for year in years:
        if target_round is not None:
            load_weekend(year, target_round, engine)
        else:
            rounds = get_season_rounds(year)
            print(f"Season {year}: {len(rounds)} rounds")
            for r in rounds:
                load_weekend(year, r, engine)


if __name__ == "__main__":
    main()
