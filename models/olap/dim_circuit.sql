{{ config(materialized='table') }}

select
    c.circuit_id                    as circuit_id_natural,
    c.circuit_name,
    c.city,
    co.country_name                 as country,
    c.length_km,
    c.turns,
    c.direction,
    c.type
from {{ source('oltp', 'circuit') }} c
join {{ source('oltp', 'country') }} co
    on c.country_id = co.country_id
