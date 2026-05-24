{{ config(materialized='table') }}

select
    sr.session_id                   as session_key,
    sr.driver_id                    as driver_key,
    sr.constructor_id               as constructor_key,
    s.race_weekend_id               as race_weekend_key,
    c.circuit_id                    as circuit_key,
    to_char(s.start_datetime::date, 'YYYYMMDD')::int as date_key,
    sr.start_position,
    sr.finish_position,
    sr.qualifying_position_before_penalties,
    (sr.finish_position - sr.start_position) as position_delta,
    sr.total_laps_completed,
    sr.fastest_lap_flag,
    (sr.outcome_status = 'dnf')     as did_not_finish_flag,
    (sr.outcome_status = 'dsq')     as disqualified_flag,
    sr.points_scored
from {{ source('oltp', 'session_result') }} sr
join {{ source('oltp', 'session') }} s on sr.session_id = s.session_id
join {{ source('oltp', 'race_weekend') }} rw on s.race_weekend_id = rw.race_weekend_id
join {{ source('oltp', 'circuit') }} c on rw.circuit_id = c.circuit_id
