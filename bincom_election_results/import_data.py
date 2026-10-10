import os
import sys

SCHEMA = """
DROP VIEW IF EXISTS current_pu_results;
DROP TABLE IF EXISTS agentname, announced_lga_results, announced_pu_results,
                     lga, ward, polling_unit, party, states CASCADE;

CREATE TABLE states (state_id INTEGER PRIMARY KEY, state_name VARCHAR(50));
CREATE TABLE lga (
    uniqueid SERIAL PRIMARY KEY, lga_id INTEGER NOT NULL, lga_name VARCHAR(50),
    state_id INTEGER, lga_description TEXT, entered_by_user VARCHAR(50),
    date_entered TIMESTAMP, user_ip_address VARCHAR(50));
CREATE TABLE ward (
    uniqueid SERIAL PRIMARY KEY, ward_id INTEGER NOT NULL, ward_name VARCHAR(50),
    lga_id INTEGER NOT NULL, ward_description TEXT, entered_by_user VARCHAR(50),
    date_entered TIMESTAMP, user_ip_address VARCHAR(50));
CREATE TABLE polling_unit (
    uniqueid SERIAL PRIMARY KEY, polling_unit_id INTEGER, ward_id INTEGER,
    lga_id INTEGER, uniquewardid INTEGER, polling_unit_number VARCHAR(50),
    polling_unit_name VARCHAR(50), polling_unit_description TEXT,
    lat VARCHAR(255), "long" VARCHAR(255), entered_by_user VARCHAR(50),
    date_entered TIMESTAMP, user_ip_address VARCHAR(50));
CREATE TABLE party (id SERIAL PRIMARY KEY, partyid VARCHAR(11), partyname VARCHAR(11));
CREATE TABLE announced_pu_results (
    result_id SERIAL PRIMARY KEY, polling_unit_uniqueid INTEGER NOT NULL,
    party_abbreviation VARCHAR(4) NOT NULL, party_score INTEGER NOT NULL,
    entered_by_user VARCHAR(50), date_entered TIMESTAMP, user_ip_address VARCHAR(50));
CREATE TABLE announced_lga_results (
    result_id SERIAL PRIMARY KEY, lga_name VARCHAR(50), party_abbreviation VARCHAR(4),
    party_score INTEGER, entered_by_user VARCHAR(50), date_entered TIMESTAMP,
    user_ip_address VARCHAR(50));
CREATE TABLE agentname (
    name_id SERIAL PRIMARY KEY, firstname VARCHAR(255), lastname VARCHAR(255),
    email VARCHAR(255), phone VARCHAR(13), pollingunit_uniqueid INTEGER);

CREATE INDEX ON polling_unit (lga_id, uniquewardid);
CREATE INDEX ON announced_pu_results (polling_unit_uniqueid);

-- Some polling units were entered more than once (e.g. unit 10).
-- The app treats the most recent submission for a unit as the current one.
CREATE VIEW current_pu_results AS
SELECT r.* FROM announced_pu_results r
JOIN (SELECT polling_unit_uniqueid, MAX(date_entered) AS latest
      FROM announced_pu_results GROUP BY polling_unit_uniqueid) m
  ON m.polling_unit_uniqueid = r.polling_unit_uniqueid AND m.latest = r.date_entered;
"""

SERIAL_KEYS = {"lga": "uniqueid", "ward": "uniqueid", "polling_unit": "uniqueid",
               "party": "id", "announced_pu_results": "result_id",
               "announced_lga_results": "result_id", "agentname": "name_id"}

ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "0": ""}


def parse_value(s, i):
    """Parse one SQL literal starting at s[i]; return (value, next_index)."""
    if s[i] == "'":
        out, i = [], i + 1
        while True:
            c = s[i]
            if c == "\\":
                out.append(ESCAPES.get(s[i + 1], s[i + 1]))
                i += 2
            elif c == "'":
                if s[i + 1:i + 2] == "'":      # '' is an escaped quote
                    out.append("'")
                    i += 2
                else:
                    return "".join(out), i + 1
            else:
                out.append(c)
                i += 1
    j = i
    while s[j] not in ",)":
        j += 1
    token = s[i:j].strip()
    if token.upper() == "NULL":
        return None, j
    try:
        return int(token), j
    except ValueError:
        return float(token), j


def parse_rows(s, i):
    """Parse '(..),(..),...;' starting at s[i]; return (rows, next_index)."""
    rows = []
    while True:
        while s[i] in " \t\r\n,":
            i += 1
        if s[i] == ";":
            return rows, i + 1
        i += 1                                  # skip "("
        row = []
        while True:
            while s[i] in " \t\r\n":
                i += 1
            value, i = parse_value(s, i)
            if isinstance(value, str) and value.startswith("0000-00-00"):
                value = None                    # MySQL zero-date is invalid in Postgres
            row.append(value)
            while s[i] in " \t\r\n":
                i += 1
            i += 1                              # consume "," or ")"
            if s[i - 1] == ")":
                break
        rows.append(tuple(row))


def parse_inserts(sql):
    """Yield (table, columns, rows) for every INSERT statement in a MySQL dump."""
    pos = 0
    while True:
        start = sql.find("INSERT INTO `", pos)
        if start == -1:
            return
        t_end = sql.index("`", start + 13)
        table = sql[start + 13:t_end]
        c_start = sql.index("(", t_end)
        c_end = sql.index(")", c_start)
        columns = [c.strip().strip("`") for c in sql[c_start + 1:c_end].split(",")]
        rows, pos = parse_rows(sql, sql.index("VALUES", c_end) + 6)
        yield table, columns, rows


def main(path):
    import psycopg2
    from psycopg2.extras import execute_values

    with open(path, encoding="utf-8", errors="replace") as f:
        sql = f.read()
    # conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
    with conn, conn.cursor() as cur:
        cur.execute(SCHEMA)
        for table, cols, rows in parse_inserts(sql):
            col_sql = ", ".join('"%s"' % c for c in cols)
            execute_values(cur, "INSERT INTO %s (%s) VALUES %%s" % (table, col_sql),
                           rows, page_size=500)
            print("%-24s %d rows" % (table, len(rows)))
        for table, key in SERIAL_KEYS.items():
            cur.execute("SELECT setval(pg_get_serial_sequence('%s', '%s'), "
                        "(SELECT MAX(%s) FROM %s))" % (table, key, key, table))
    conn.close()
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python import_data.py bincom_test.sql")
    main(sys.argv[1])
