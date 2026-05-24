{{ config(materialized='table') }}

select
    rw.race_weekend_id              as race_weekend_id_natural,
    rw.weekend_name,
    rw.season_year,
    rw.round_number,
    rw.is_sprint_weekend,
    to_char(rw.start_date, 'YYYYMMDD')::int as start_date_key,
    rw.circuit_id                   as circuit_key
from {{ source('oltp', 'race_weekend') }} rw
