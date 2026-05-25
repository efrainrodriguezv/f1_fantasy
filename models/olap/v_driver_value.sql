{{ config(materialized='view') }}

-- Per-driver performance and value (PPD) for fantasy decision support.
-- "Market vs. historical": current price (2026) vs. 2024-2025 performance.

with latest_price as (
    select distinct on (driver_id)
        driver_id,
        price as current_price
    from {{ source('oltp', 'driver_price_change') }}
    order by driver_id, effective_from desc
),

driver_perf as (
    select
        sr.driver_id,
        rw.season_year,
        count(*) as races_run,
        sum(sr.points_scored) as total_points,
        avg(sr.points_scored)::decimal(6,2) as avg_points_per_race,
        sum(case when sr.finish_position = 1 then 1 else 0 end) as wins,
        sum(case when sr.finish_position <= 3 then 1 else 0 end) as podiums,
        sum(case when sr.outcome_status = 'dnf' then 1 else 0 end) as dnfs,
        avg(sr.finish_position - sr.start_position)::decimal(4,2) as avg_position_change
    from {{ source('oltp', 'session_result') }} sr
    join {{ source('oltp', 'session') }} s on sr.session_id = s.session_id
    join {{ source('oltp', 'session_type') }} st on s.session_type_id = st.session_type_id
    join {{ source('oltp', 'race_weekend') }} rw on s.race_weekend_id = rw.race_weekend_id
    where st.type_name = 'race'
    group by sr.driver_id, rw.season_year
)

select
    d.driver_id,
    d.first_name || ' ' || d.last_name as driver_name,
    dp.season_year,
    dp.races_run,
    dp.total_points,
    dp.avg_points_per_race,
    dp.wins,
    dp.podiums,
    dp.dnfs,
    dp.avg_position_change,
    lp.current_price,
    case
        when lp.current_price is null or lp.current_price = 0 then null
        else (dp.total_points / lp.current_price)::decimal(6,2)
    end as points_per_million,
    case
        when lp.current_price is null then 'No price'
        when (dp.total_points / lp.current_price) > 20 then 'Undervalued'
        when (dp.total_points / lp.current_price) > 10 then 'Fair value'
        else 'Overvalued'
    end as value_tier
from driver_perf dp
join {{ source('oltp', 'driver') }} d on dp.driver_id = d.driver_id
left join latest_price lp on dp.driver_id = lp.driver_id
