{{ config(materialized='table') }}

with current_engine as (
    -- pick the most recent season's engine per constructor
    select distinct on (constructor_id)
        constructor_id,
        engine_name,
        season_year
    from {{ source('oltp', 'constructor_season') }}
    order by constructor_id, season_year desc
)

select
    c.constructor_id                as constructor_id_natural,
    c.constructor_name,
    c.short_name,
    lc.country_name                 as licensed_country,
    hc.country_name                 as headquarters_country,
    ce.engine_name                  as current_engine
from {{ source('oltp', 'constructor') }} c
join {{ source('oltp', 'country') }} lc
    on c.licensed_country_id = lc.country_id
left join {{ source('oltp', 'country') }} hc
    on c.headquarters_country_id = hc.country_id
left join current_engine ce
    on c.constructor_id = ce.constructor_id
