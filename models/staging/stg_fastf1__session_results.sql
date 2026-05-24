{{ config(materialized='view') }}

-- Cleans FastF1 raw session results into a typed, normalized staging table.
-- Handles three FastF1 quirks:
--   1. INT64_MIN (-9223372036854775808) as null sentinel for missing times
--   2. Empty Status string for non-race/sprint sessions (practice, qualifying)
--   3. Status as free text → 4-bucket outcome_status (finished/dnf/dsq/dns)

with raw_data as (
    select * from {{ source('raw', 'fastf1_session_results') }}
),

cleaned as (
    select
        -- Identifiers
        season_year::int                              as season_year,
        round_number::int                             as round_number,
        session_type_code                             as session_type_code,
        event_name                                    as event_name,
        session_start at time zone 'UTC'              as session_start,

        -- Driver identity
        "DriverId"                                    as fastf1_driver_id,
        "DriverNumber"::smallint                      as driver_number,
        "FirstName"                                   as first_name,
        "LastName"                                    as last_name,
        "FullName"                                    as full_name,
        "Abbreviation"                                as driver_abbreviation,
        "CountryCode"                                 as country_code,

        -- Constructor / Team
        "TeamId"                                      as fastf1_team_id,
        "TeamName"                                    as team_name,

        -- Positions
        "Position"::smallint                          as finish_position,
        "GridPosition"::smallint                      as grid_position,
        "ClassifiedPosition"                          as classified_position,

        -- Times in nanoseconds → seconds; INT64_MIN means null
        case when "Q1" = -9223372036854775808 then null
             else "Q1"::numeric / 1e9 end             as q1_seconds,
        case when "Q2" = -9223372036854775808 then null
             else "Q2"::numeric / 1e9 end             as q2_seconds,
        case when "Q3" = -9223372036854775808 then null
             else "Q3"::numeric / 1e9 end             as q3_seconds,
        case when "Time" = -9223372036854775808 then null
             else "Time"::numeric / 1e9 end           as total_time_seconds,

        -- Status → 4 canonical buckets, or NULL if not applicable.
        -- Practice and qualifying sessions return empty Status because
        -- "finished/dnf" isn't a meaningful concept for them.
        case
            when coalesce("Status", '') = ''                            then null
            when "Status" in ('Did not start', 'DNS')                   then 'dns'
            when "Status" in ('Disqualified', 'DSQ', 'Excluded')        then 'dsq'
            when "Status" = 'Finished'                                   then 'finished'
            when "Status" like '+%Lap%'                                  then 'finished'
            when "Status" like '+%Laps%'                                 then 'finished'
            else 'dnf'
        end                                            as outcome_status,
        "Status"                                       as original_status,

        -- Other
        "Points"::decimal(5,2)                        as points_scored,
        "Laps"::smallint                              as laps_completed

    from raw_data
)

select * from cleaned
