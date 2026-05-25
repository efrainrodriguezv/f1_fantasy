{{ config(materialized='view') }}

-- Cumulative season points and 5-race rolling average per driver per round.
-- Useful for "who's trending up/down" analysis.

with race_results as (
    select
        sr.driver_id,
        rw.season_year,
        rw.round_number,
        rw.weekend_name,
        rw.start_date,
        sr.points_scored,
        sr.finish_position
    from {{ source('oltp', 'session_result') }} sr
    join {{ source('oltp', 'session') }} s on sr.session_id = s.session_id
    join {{ source('oltp', 'session_type') }} st on s.session_type_id = st.session_type_id
    join {{ source('oltp', 'race_weekend') }} rw on s.race_weekend_id = rw.race_weekend_id
    where st.type_name = 'race'
)

select
    rr.driver_id,
    d.first_name || ' ' || d.last_name as driver_name,
    rr.season_year,
    rr.round_number,
    rr.weekend_name,
    rr.start_date,
    rr.points_scored,
    rr.finish_position,
    sum(rr.points_scored) over (
        partition by rr.driver_id, rr.season_year
        order by rr.round_number
    ) as cumulative_season_points,
    avg(rr.points_scored) over (
        partition by rr.driver_id, rr.season_year
        order by rr.round_number
        rows between 4 preceding and current row
    )::decimal(5,2) as rolling_5_race_avg
from race_results rr
join {{ source('oltp', 'driver') }} d on rr.driver_id = d.driver_id
