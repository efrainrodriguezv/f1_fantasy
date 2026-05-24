{{ config(materialized='table') }}

select
    s.session_id                    as session_id_natural,
    s.race_weekend_id               as race_weekend_key,
    to_char(s.start_datetime::date, 'YYYYMMDD')::int as date_key,
    st.type_name                    as session_type,
    st.is_points_scoring,
    s.start_datetime
from {{ source('oltp', 'session') }} s
join {{ source('oltp', 'session_type') }} st
    on s.session_type_id = st.session_type_id
