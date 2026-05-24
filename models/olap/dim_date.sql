{{ config(materialized='table') }}

-- generate a date dimension spanning 2020-01-01 to 2026-12-31
-- using postgres generate_series

with date_spine as (
    select generate_series(
        '2020-01-01'::date,
        '2026-12-31'::date,
        '1 day'::interval
    )::date as full_date
)

select
    -- YYYYMMDD integer key
    to_char(full_date, 'YYYYMMDD')::int     as date_key,
    full_date,
    to_char(full_date, 'Day')               as day_of_week,
    extract(day from full_date)::smallint   as day_of_month,
    extract(month from full_date)::smallint as month_number,
    to_char(full_date, 'Month')             as month_name,
    extract(quarter from full_date)::smallint as quarter,
    extract(year from full_date)::int       as year,
    extract(year from full_date)::int       as f1_season_year,
    false                                   as is_race_weekend,  -- populated by separate logic in prod
    extract(dow from full_date) in (0, 6)   as is_weekend
from date_spine
