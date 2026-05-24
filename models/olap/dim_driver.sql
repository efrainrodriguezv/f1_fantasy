{{ config(materialized='table') }}

select
    d.driver_id                              as driver_id_natural,
    d.first_name || ' ' || d.last_name       as full_name,
    d.first_name,
    d.last_name,
    c.country_name                           as nationality,
    d.date_of_birth,
    d.permanent_number,
    d.f1_debut_date,
    true                                     as is_active
from {{ source('oltp', 'driver') }} d
join {{ source('oltp', 'country') }} c
    on d.nationality_country_id = c.country_id
