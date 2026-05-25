"""
Load OLTP tables from the dbt staging view.

Reads from staging.stg_fastf1__session_results and populates:
  country, constructor, driver, circuit, race_weekend, session, session_result

Uses ON CONFLICT DO NOTHING for idempotency — script can be re-run safely.
"""
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


CIRCUIT_MAP = {
    "Bahrain Grand Prix":         ("Bahrain International Circuit",      "Sakhir",       "BH"),
    "Saudi Arabian Grand Prix":   ("Jeddah Corniche Circuit",            "Jeddah",       "SA"),
    "Australian Grand Prix":      ("Albert Park Circuit",                "Melbourne",    "AU"),
    "Japanese Grand Prix":        ("Suzuka International Racing Course", "Suzuka",       "JP"),
    "Chinese Grand Prix":         ("Shanghai International Circuit",     "Shanghai",     "CN"),
    "Miami Grand Prix":           ("Miami International Autodrome",      "Miami",        "US"),
    "Emilia Romagna Grand Prix":  ("Autodromo Enzo e Dino Ferrari",      "Imola",        "IT"),
    "Monaco Grand Prix":          ("Circuit de Monaco",                  "Monte Carlo",  "MC"),
    "Canadian Grand Prix":        ("Circuit Gilles Villeneuve",          "Montreal",     "CA"),
    "Spanish Grand Prix":         ("Circuit de Barcelona-Catalunya",     "Barcelona",    "ES"),
    "Austrian Grand Prix":        ("Red Bull Ring",                      "Spielberg",    "AT"),
    "British Grand Prix":         ("Silverstone Circuit",                "Silverstone",  "GB"),
    "Hungarian Grand Prix":       ("Hungaroring",                        "Mogyorod",     "HU"),
    "Belgian Grand Prix":         ("Circuit de Spa-Francorchamps",       "Spa",          "BE"),
    "Dutch Grand Prix":           ("Circuit Zandvoort",                  "Zandvoort",    "NL"),
    "Italian Grand Prix":         ("Autodromo Nazionale Monza",          "Monza",        "IT"),
    "Azerbaijan Grand Prix":      ("Baku City Circuit",                  "Baku",         "AZ"),
    "Singapore Grand Prix":       ("Marina Bay Street Circuit",          "Singapore",    "SG"),
    "United States Grand Prix":   ("Circuit of the Americas",            "Austin",       "US"),
    "Mexico City Grand Prix":     ("Autodromo Hermanos Rodriguez",       "Mexico City",  "MX"),
    "São Paulo Grand Prix":       ("Autodromo Jose Carlos Pace",         "São Paulo",    "BR"),
    "Las Vegas Grand Prix":       ("Las Vegas Strip Circuit",            "Las Vegas",    "US"),
    "Qatar Grand Prix":           ("Lusail International Circuit",       "Lusail",       "QA"),
    "Abu Dhabi Grand Prix":       ("Yas Marina Circuit",                 "Abu Dhabi",    "AE"),
}

COUNTRY_CODE_MAP = {
    "NED": ("Netherlands",         "NL"),
    "GBR": ("United Kingdom",      "GB"),
    "MEX": ("Mexico",              "MX"),
    "MON": ("Monaco",              "MC"),
    "ESP": ("Spain",               "ES"),
    "FRA": ("France",              "FR"),
    "GER": ("Germany",             "DE"),
    "ITA": ("Italy",               "IT"),
    "FIN": ("Finland",             "FI"),
    "AUS": ("Australia",           "AU"),
    "JPN": ("Japan",               "JP"),
    "DEN": ("Denmark",             "DK"),
    "CAN": ("Canada",              "CA"),
    "USA": ("United States",       "US"),
    "CHN": ("China",               "CN"),
    "THA": ("Thailand",            "TH"),
    "BRA": ("Brazil",              "BR"),
    "ARG": ("Argentina",           "AR"),
    "NZL": ("New Zealand",         "NZ"),
    "BEL": ("Belgium",             "BE"),
    "POL": ("Poland",              "PL"),
    "AUT": ("Austria",             "AT"),
}


def get_engine():
    load_dotenv()
    user = os.environ["SUPABASE_USER"]
    password = os.environ["SUPABASE_PASSWORD"]
    host = os.environ["SUPABASE_HOST"]
    port = os.environ["SUPABASE_PORT"]
    db = os.environ["SUPABASE_DB"]
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def load_countries(conn):
    print("Loading countries...")
    driver_codes_query = conn.execute(text("""
        SELECT DISTINCT country_code FROM staging.stg_fastf1__session_results
        WHERE country_code IS NOT NULL AND country_code != 'nan'
    """))
    driver_country_codes = {row[0] for row in driver_codes_query}

    circuit_country_isos = {info[2] for info in CIRCUIT_MAP.values()}

    countries_to_insert = []
    for code in driver_country_codes:
        if code in COUNTRY_CODE_MAP:
            countries_to_insert.append(COUNTRY_CODE_MAP[code])
    for iso2 in circuit_country_isos:
        name = next((v[0] for v in COUNTRY_CODE_MAP.values() if v[1] == iso2), iso2)
        countries_to_insert.append((name, iso2))

    countries_to_insert = list(set(countries_to_insert))

    for name, iso2 in countries_to_insert:
        conn.execute(text("""
            INSERT INTO oltp.country (country_name, iso_code)
            VALUES (:name, :iso) ON CONFLICT (iso_code) DO NOTHING
        """), {"name": name, "iso": iso2})

    print(f"  -> attempted {len(countries_to_insert)} countries")


def load_constructors(conn):
    print("Loading constructors...")
    gb_id = conn.execute(text("""
        SELECT country_id FROM oltp.country WHERE iso_code = 'GB'
    """)).scalar()

    teams_df = pd.read_sql(text("""
        SELECT DISTINCT team_name, fastf1_team_id
        FROM staging.stg_fastf1__session_results
        WHERE team_name IS NOT NULL AND team_name != 'nan'
    """), conn)

    for _, row in teams_df.iterrows():
        conn.execute(text("""
            INSERT INTO oltp.constructor (constructor_name, short_name, licensed_country_id)
            VALUES (:name, :short, :country)
            ON CONFLICT (constructor_name) DO NOTHING
        """), {"name": row["team_name"], "short": row["team_name"][:50], "country": gb_id})

    print(f"  -> {len(teams_df)} constructors")


def load_drivers(conn):
    print("Loading drivers...")
    drivers_df = pd.read_sql(text("""
        SELECT DISTINCT first_name, last_name, driver_number, country_code
        FROM staging.stg_fastf1__session_results
        WHERE first_name IS NOT NULL AND first_name != 'nan'
    """), conn)

    for _, row in drivers_df.iterrows():
        iso2 = COUNTRY_CODE_MAP.get(row["country_code"], (None, None))[1]
        if iso2 is None:
            print(f"  ! Skipping {row['first_name']} {row['last_name']}: unknown country {row['country_code']}")
            continue

        country_id = conn.execute(text("""
            SELECT country_id FROM oltp.country WHERE iso_code = :iso
        """), {"iso": iso2}).scalar()

        if country_id is None:
            continue

        conn.execute(text("""
            INSERT INTO oltp.driver
              (first_name, last_name, nationality_country_id, permanent_number)
            VALUES (:fn, :ln, :country, :num)
            ON CONFLICT DO NOTHING
        """), {
            "fn": row["first_name"],
            "ln": row["last_name"],
            "country": country_id,
            "num": int(row["driver_number"]) if pd.notna(row["driver_number"]) else None,
        })

    print(f"  -> {len(drivers_df)} drivers")


def load_circuits(conn):
    print("Loading circuits...")
    events_df = pd.read_sql(text("""
        SELECT DISTINCT event_name FROM staging.stg_fastf1__session_results
    """), conn)

    inserted = 0
    for _, row in events_df.iterrows():
        event = row["event_name"]
        if event not in CIRCUIT_MAP:
            print(f"  ! No circuit mapping for '{event}'; skipping")
            continue
        circuit_name, city, country_iso = CIRCUIT_MAP[event]
        country_id = conn.execute(text("""
            SELECT country_id FROM oltp.country WHERE iso_code = :iso
        """), {"iso": country_iso}).scalar()

        conn.execute(text("""
            INSERT INTO oltp.circuit
              (circuit_name, city, country_id, length_km, direction, type)
            VALUES (:name, :city, :country, :len, :dir, :type)
            ON CONFLICT (circuit_name) DO NOTHING
        """), {
            "name": circuit_name, "city": city, "country": country_id,
            "len": 5.0, "dir": "clockwise", "type": "permanent",
        })
        inserted += 1

    print(f"  -> {inserted} circuits")


def load_race_weekends(conn):
    print("Loading race weekends...")
    weekends_df = pd.read_sql(text("""
        SELECT DISTINCT season_year, round_number, event_name,
               MIN(session_start::date) AS start_date
        FROM staging.stg_fastf1__session_results
        GROUP BY season_year, round_number, event_name
    """), conn)

    for _, row in weekends_df.iterrows():
        if row["event_name"] not in CIRCUIT_MAP:
            continue
        circuit_name = CIRCUIT_MAP[row["event_name"]][0]
        circuit_id = conn.execute(text("""
            SELECT circuit_id FROM oltp.circuit WHERE circuit_name = :name
        """), {"name": circuit_name}).scalar()

        conn.execute(text("""
            INSERT INTO oltp.race_weekend
              (weekend_name, season_year, round_number, start_date, circuit_id)
            VALUES (:name, :year, :round, :date, :circuit)
            ON CONFLICT (season_year, round_number) DO NOTHING
        """), {
            "name": f"{row['season_year']} {row['event_name']}",
            "year": int(row["season_year"]),
            "round": int(row["round_number"]),
            "date": row["start_date"],
            "circuit": circuit_id,
        })

    print(f"  -> {len(weekends_df)} race weekends")


def load_sessions(conn):
    print("Loading sessions...")
    sessions_df = pd.read_sql(text("""
        SELECT DISTINCT season_year, round_number, session_type_code,
               MIN(session_start) AS start_datetime
        FROM staging.stg_fastf1__session_results
        WHERE session_type_code IN ('Q', 'S', 'R')
        GROUP BY season_year, round_number, session_type_code
    """), conn)

    type_map = {"Q": "qualifying", "S": "sprint", "R": "race"}

    for _, row in sessions_df.iterrows():
        rw_id = conn.execute(text("""
            SELECT race_weekend_id FROM oltp.race_weekend
            WHERE season_year = :year AND round_number = :round
        """), {"year": int(row["season_year"]), "round": int(row["round_number"])}).scalar()

        if rw_id is None:
            continue

        st_id = conn.execute(text("""
            SELECT session_type_id FROM oltp.session_type WHERE type_name = :name
        """), {"name": type_map[row["session_type_code"]]}).scalar()

        conn.execute(text("""
            INSERT INTO oltp.session
              (race_weekend_id, session_type_id, start_datetime)
            VALUES (:rw, :st, :dt)
            ON CONFLICT (race_weekend_id, session_type_id) DO NOTHING
        """), {"rw": rw_id, "st": st_id, "dt": row["start_datetime"]})

    print(f"  -> {len(sessions_df)} sessions")


def load_session_results(conn):
    print("Loading session results...")
    results_df = pd.read_sql(text("""
        SELECT
            s.season_year, s.round_number, s.session_type_code,
            s.first_name, s.last_name, s.team_name,
            s.grid_position, s.finish_position, s.outcome_status,
            s.laps_completed, s.points_scored
        FROM staging.stg_fastf1__session_results s
        WHERE s.session_type_code IN ('S', 'R')
          AND s.first_name IS NOT NULL AND s.first_name != 'nan'
    """), conn)

    type_map = {"Q": "qualifying", "S": "sprint", "R": "race"}
    inserted = 0

    for _, row in results_df.iterrows():
        session_id = conn.execute(text("""
            SELECT s.session_id FROM oltp.session s
            JOIN oltp.race_weekend rw ON s.race_weekend_id = rw.race_weekend_id
            JOIN oltp.session_type st ON s.session_type_id = st.session_type_id
            WHERE rw.season_year = :year AND rw.round_number = :round
              AND st.type_name = :stype
        """), {
            "year": int(row["season_year"]),
            "round": int(row["round_number"]),
            "stype": type_map[row["session_type_code"]],
        }).scalar()

        driver_id = conn.execute(text("""
            SELECT driver_id FROM oltp.driver
            WHERE first_name = :fn AND last_name = :ln
        """), {"fn": row["first_name"], "ln": row["last_name"]}).scalar()

        constructor_id = conn.execute(text("""
            SELECT constructor_id FROM oltp.constructor WHERE constructor_name = :name
        """), {"name": row["team_name"]}).scalar()

        if not all([session_id, driver_id, constructor_id]):
            continue

        conn.execute(text("""
            INSERT INTO oltp.session_result
              (session_id, driver_id, constructor_id,
               start_position, finish_position, outcome_status,
               total_laps_completed, points_scored)
            VALUES (:s, :d, :c, :start, :finish, :status, :laps, :points)
            ON CONFLICT (session_id, driver_id) DO NOTHING
        """), {
            "s": session_id, "d": driver_id, "c": constructor_id,
            "start": int(row["grid_position"]) if pd.notna(row["grid_position"]) else None,
            "finish": int(row["finish_position"]) if pd.notna(row["finish_position"]) else None,
            "status": row["outcome_status"],
            "laps": int(row["laps_completed"]) if pd.notna(row["laps_completed"]) else None,
            "points": float(row["points_scored"]) if pd.notna(row["points_scored"]) else 0,
        })
        inserted += 1

    print(f"  -> attempted {inserted} session_result rows")


def main():
    engine = get_engine()
    with engine.begin() as conn:
        load_countries(conn)
        load_constructors(conn)
        load_drivers(conn)
        load_circuits(conn)
        load_race_weekends(conn)
        load_sessions(conn)
        load_session_results(conn)
    print("Done.")


if __name__ == "__main__":
    main()
