import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg2.extras import RealDictCursor, execute_values
from pydantic import BaseModel, field_validator

PARTIES = ["PDP", "DPP", "ACN", "PPA", "CDC", "JP", "ANPP", "LABO", "CPP"]
DELTA_STATE_ID = 25
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Delta State 2011 Results")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@contextmanager
def db() -> Iterator[Any]:
    """One short-lived connection per request; commits on success, rolls back on error."""
    conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""), cursor_factory=RealDictCursor)
    try:
        with conn, conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


@app.get("/", include_in_schema=False)
def page_unit():
    return FileResponse(STATIC / "index.html")


@app.get("/lga", include_in_schema=False)
def page_lga():
    return FileResponse(STATIC / "lga.html")


@app.get("/new", include_in_schema=False)
def page_new():
    return FileResponse(STATIC / "new.html")


@app.get("/api/parties")
def parties():
    return PARTIES


@app.get("/api/lgas")
def lgas():
    with db() as cur:
        cur.execute("SELECT lga_id AS id, lga_name AS name FROM lga "
                    "WHERE state_id = %s ORDER BY lga_name", (DELTA_STATE_ID,))
        return cur.fetchall()


@app.get("/api/lgas/{lga_id}/wards")
def wards(lga_id: int, with_units: bool = False):
    """with_units=true -> only wards that have polling units (for viewing results)."""
    with db() as cur:
        if with_units:
            cur.execute("""SELECT DISTINCT w.uniqueid AS id, w.ward_name AS name
                           FROM polling_unit pu JOIN ward w ON w.uniqueid = pu.uniquewardid
                           WHERE pu.lga_id = %s ORDER BY name""", (lga_id,))
        else:
            cur.execute("SELECT uniqueid AS id, ward_name AS name FROM ward "
                        "WHERE lga_id = %s ORDER BY name", (lga_id,))
        return cur.fetchall()


@app.get("/api/wards/{ward_id}/polling-units")
def polling_units(ward_id: int, lga_id: int):
    with db() as cur:
        cur.execute("""SELECT uniqueid AS id,
                              COALESCE(NULLIF(TRIM(polling_unit_name), ''), 'Unnamed') AS name,
                              polling_unit_number AS number
                       FROM polling_unit
                       WHERE uniquewardid = %s AND lga_id = %s ORDER BY name, id""",
                    (ward_id, lga_id))
        return cur.fetchall()


@app.get("/api/polling-units/{pu_id}/results")
def unit_results(pu_id: int):
    with db() as cur:
        cur.execute("""SELECT pu.uniqueid AS id, pu.polling_unit_name AS name,
                              pu.polling_unit_number AS number,
                              w.ward_name AS ward, l.lga_name AS lga
                       FROM polling_unit pu
                       LEFT JOIN ward w ON w.uniqueid = pu.uniquewardid
                       LEFT JOIN lga l ON l.lga_id = pu.lga_id
                       WHERE pu.uniqueid = %s""", (pu_id,))
        unit = cur.fetchone()
        if not unit:
            raise HTTPException(404, "Polling unit not found")
        cur.execute("""SELECT party_abbreviation AS party, party_score AS score
                       FROM current_pu_results WHERE polling_unit_uniqueid = %s
                       ORDER BY party_score DESC""", (pu_id,))
        return {"unit": unit, "results": cur.fetchall()}


@app.get("/api/lgas/{lga_id}/total")
def lga_total(lga_id: int):
    """Sum of polling unit results under an LGA (announced_lga_results is NOT used)."""
    with db() as cur:
        cur.execute("SELECT lga_name FROM lga WHERE lga_id = %s", (lga_id,))
        lga = cur.fetchone()
        if not lga:
            raise HTTPException(404, "Local government not found")
        cur.execute("""SELECT r.party_abbreviation AS party, SUM(r.party_score) AS total
                       FROM current_pu_results r
                       JOIN polling_unit pu ON pu.uniqueid = r.polling_unit_uniqueid
                       WHERE pu.lga_id = %s
                       GROUP BY r.party_abbreviation ORDER BY total DESC""", (lga_id,))
        results = cur.fetchall()
        cur.execute("""SELECT COUNT(DISTINCT r.polling_unit_uniqueid) AS n
                       FROM current_pu_results r
                       JOIN polling_unit pu ON pu.uniqueid = r.polling_unit_uniqueid
                       WHERE pu.lga_id = %s""", (lga_id,))
        return {"lga": lga["lga_name"], "polling_units": cur.fetchone()["n"],
                "results": results}


class NewResult(BaseModel):
    lga_id: int
    ward_id: int                      # ward.uniqueid
    name: str
    number: Optional[str] = None
    entered_by: str
    scores: Dict[str, int]

    @field_validator("name", "entered_by")
    @classmethod
    def not_blank(cls, v):
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Name fields must be 2-50 characters")
        return v

    @field_validator("scores")
    @classmethod
    def all_parties(cls, v):
        if set(v) != set(PARTIES):
            raise ValueError("A score is required for every party")
        if any(s < 0 for s in v.values()):
            raise ValueError("Scores cannot be negative")
        return v


@app.post("/api/polling-units", status_code=201)
def create_polling_unit(body: NewResult, request: Request):
    ip = request.client.host if request.client else ""
    with db() as cur:
        cur.execute("SELECT ward_id FROM ward WHERE uniqueid = %s AND lga_id = %s",
                    (body.ward_id, body.lga_id))
        ward = cur.fetchone()
        if not ward:
            raise HTTPException(400, "That ward does not belong to the chosen local government")
        cur.execute("SELECT COALESCE(MAX(polling_unit_id), 0) + 1 AS n "
                    "FROM polling_unit WHERE uniquewardid = %s", (body.ward_id,))
        seq = cur.fetchone()["n"]
        number = (body.number or "").strip() or "DT%02d%02d%03d" % (body.lga_id, ward["ward_id"], seq)
        cur.execute("""INSERT INTO polling_unit
                         (polling_unit_id, ward_id, lga_id, uniquewardid, polling_unit_number,
                          polling_unit_name, entered_by_user, date_entered, user_ip_address)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s) RETURNING uniqueid""",
                    (seq, ward["ward_id"], body.lga_id, body.ward_id, number,
                     body.name, body.entered_by, ip))
        pu_id = cur.fetchone()["uniqueid"]
        execute_values(
            cur,
            """INSERT INTO announced_pu_results
                 (polling_unit_uniqueid, party_abbreviation, party_score,
                  entered_by_user, date_entered, user_ip_address) VALUES %s""",
            [(pu_id, p, body.scores[p], body.entered_by, ip) for p in PARTIES],
            template="(%s, %s, %s, %s, NOW(), %s)")
    return {"polling_unit_id": pu_id, "name": body.name, "number": number}
