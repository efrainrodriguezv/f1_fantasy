# F1 Fantasy Optimization

End-to-end data platform for Formula 1 Fantasy team optimization.
Course project for ADSP 31012 (Data Engineering Platforms for Analytics),
University of Chicago MS in Applied Data Science, Spring 2026.

## Architecture

- **Sources**: Ergast API (historical), FastF1 (current), Kalshi (prediction markets)
- **Warehouse**: Snowflake
- **Transformation**: dbt (OLTP 3NF → OLAP star schema)
- **Visualization**: Tableau / Streamlit

## Project structure

- `extract/` — Python scripts pulling from external APIs into Snowflake raw schema
- `models/` — dbt models (staging → oltp → olap)
- `analysis/` — exploratory queries
- `docs/` — design documents, EER diagrams, decision logs

## Setup

to be filled !! :D 

## Team

Efrain Rodriguez, Mateo Ronquillo, Robert Scott, Ananya Sen
# f1_fantasy
# f1_fantasy
# f1_fantasy
