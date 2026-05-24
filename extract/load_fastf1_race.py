"""
Extract one race weekend's data from FastF1 and load to Supabase raw schema.

Usage:
    python extract/load_fastf1_race.py 2024 1    # 2024 season, round 1 (Bahrain)
"""
import os
import sys
from pathlib import Path

import fastf1
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


def get_engine():
    """Build SQLAlchemy engine for Supabase from env vars."""
    load_dotenv()
    user = os.environ["SUPABASE_USER"]
    password = os.environ["SUPABASE_PASSWORD"]
    host = os.environ["SUPABASE_HOST"]
    port = os.environ["SUPABASE_PORT"]
    db = os.environ["SUPABASE_DB"]
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def enable_cache():
    """Point FastF1 at a local cache directory to speed up repeated calls."""
    cache_dir = Path(__file__).parent.parent / ".fastf1_cache"
    cache_dir.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))


def load_session_results(year: int, round_number: int, session_type: str, engine):
    """
    Pull session results for one session and write to raw.fastf1_session_results.

    session_type: 'Q' for qualifying, 'R' for race, 'S' for sprint, etc.
    """
    print(f"Loading {year} R{round_number} {session_type}...")
    session = fastf1.get_session(year, round_number, session_type)
    session.load(laps=False, telemetry=False, weather=False)  # results only — fast

    results = session.results.copy()
    # Add metadata so we can tell which race this row came from
    results["season_year"] = year
    results["round_number"] = round_number
    results["session_type_code"] = session_type
    results["event_name"] = session.event["EventName"]
    results["session_start"] = session.date  # already a datetime

    # Convert all columns to strings of safe types for bulk insert
    # (FastF1 returns some columns with types pandas-to-sql doesn't handle well)
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
    print(f"  -> wrote {len(results)} rows")


def main():
    if len(sys.argv) != 3:
        print("Usage: python load_fastf1_race.py <year> <round>")
        sys.exit(1)

    year = int(sys.argv[1])
    round_number = int(sys.argv[2])

    enable_cache()
    engine = get_engine()

    # Pull qualifying and race for this weekend
    for session_type in ["Q", "R"]:
        try:
            load_session_results(year, round_number, session_type, engine)
        except Exception as e:
            print(f"  -> skipped {session_type}: {e}")


if __name__ == "__main__":
    main()
