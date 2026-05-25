{{ config(materialized='view') }}

-- Per-constructor per-race aggregation for consistency analysis.
-- One row per (constructor, season, race_weekend) — both drivers' points combined.

with race_results as (
    select
        sr.constructor_id,
        rw.season_year,
        rw.round_number,
        rw.weekend_name,
        sum(sr.points_scored) as constructor_race_points,
        min(sr.finish_position) as best_finish,
        sum(case when sr.outcome_status = 'dnf' then 1 else 0 end) as drivers_dnf
    from {{ source('oltp', 'session_result') }} sr
    join {{ source('oltp', 'session') }} s on sr.session_id = s.session_id
    join {{ source('oltp', 'session_type') }} st on s.session_type_id = st.session_type_id
    join {{ source('oltp', 'race_weekend') }} rw on s.race_weekend_id = rw.race_weekend_id
    where st.type_name = 'race'
    group by sr.constructor_id, rw.season_year, rw.round_number, rw.weekend_name
)

select
    rr.constructor_id,
    c.constructor_name,
    c.short_name,
    rr.season_year,
    rr.round_number,
    rr.weekend_name,
    rr.constructor_race_points,
    rr.best_finish,
    rr.drivers_dnf
from race_results rr
join {{ source('oltp', 'constructor') }} c on rr.constructor_id = c.constructor_id
