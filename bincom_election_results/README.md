# Delta State 2011 Election Results (FastAPI + PostgreSQL)

Pages: `/` polling unit result (Q1) · `/lga` LGA total (Q2) · `/new` add a result (Q3)

## Run locally

    pip install -r requirements.txt
    export DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"   # Neon URL
    python import_data.py bincom_test.sql      # one-off: loads the data
    uvicorn main:app --reload                  # http://127.0.0.1:8000

## Deploy (e.g. Render)

Build command `pip install -r requirements.txt`
Start command `uvicorn main:app --host 0.0.0.0 --port $PORT`
Environment variable `DATABASE_URL` = your Neon connection string.

## Notes

- The MySQL dump is converted to PostgreSQL by `import_data.py`.
- Q2 sums `announced_pu_results` per LGA; `announced_lga_results` is not used.
- Polling unit 10 was submitted twice; the most recent submission is treated as current
  (see the `current_pu_results` view in `import_data.py`).
- Party code `LABO` is used (the results table stores 4-character codes).
