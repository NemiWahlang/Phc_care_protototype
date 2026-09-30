import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "phc_care.db"

# sample data: village, district, doctor, starting status
SEED_PHCS = [
    ("Smit", "East Khasi Hills", "Dr. B. Marbaniang", "Active"),
    ("Mawryngkneng", "East Khasi Hills", "Dr. K. Lyngdoh", "Inactive"),
    ("Sohra", "East Khasi Hills", "Dr. P. Suchiang", "Active"),
    ("Mairang", "West Khasi Hills", "Dr. W. Nongrum", "Inactive"),
    ("Nongstoin", "West Khasi Hills", "Dr. D. Kharshiing", "Active"),
    ("Jowai", "West Jaintia Hills", "Dr. S. Pariat", "Active"),
    ("Nongpoh", "Ri-Bhoi", "Dr. R. Sangma", "Inactive"),
    ("Williamnagar", "East Garo Hills", "Dr. T. Momin", "Active"),
    ("Tura", "West Garo Hills", "Dr. A. Marak", "Inactive"),
    ("Baghmara", "South Garo Hills", "Dr. J. Ch. Sangma", "Active"),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us use row["name"]
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS PHCs (
            phc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            village_name TEXT NOT NULL,
            district TEXT NOT NULL
        )
    """)

    # every status change is a new row, so we keep a full history
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Doctors_Log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            phc_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Active', 'Inactive')),
            last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (phc_id) REFERENCES PHCs(phc_id)
        )
    """)

    # only add sample data if the table is empty
    cur.execute("SELECT COUNT(*) FROM PHCs")
    if cur.fetchone()[0] == 0:
        for village, district, doctor, status in SEED_PHCS:
            cur.execute(
                "INSERT INTO PHCs (village_name, district) VALUES (?, ?)",
                (village, district),
            )
            cur.execute(
                "INSERT INTO Doctors_Log (phc_id, doctor_name, status) VALUES (?, ?, ?)",
                (cur.lastrowid, doctor, status),
            )
        conn.commit()

    conn.close()


def get_all_phcs_with_status():
    # join each PHC with its latest log row
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.phc_id, p.village_name, p.district,
               d.doctor_name, d.status, d.last_updated
        FROM PHCs p
        JOIN Doctors_Log d ON d.phc_id = p.phc_id
        WHERE d.log_id = (
            SELECT MAX(log_id) FROM Doctors_Log WHERE phc_id = p.phc_id
        )
        ORDER BY p.village_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_status(phc_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT doctor_name, status FROM Doctors_Log WHERE phc_id = ? ORDER BY log_id DESC LIMIT 1",
        (phc_id,),
    ).fetchone()

    if row is None:
        conn.close()
        raise ValueError(f"No PHC found with id {phc_id}")

    new_status = "Inactive" if row["status"] == "Active" else "Active"
    conn.execute(
        "INSERT INTO Doctors_Log (phc_id, doctor_name, status) VALUES (?, ?, ?)",
        (phc_id, row["doctor_name"], new_status),
    )
    conn.commit()
    conn.close()
    return {"phc_id": phc_id, "status": new_status}


def find_status_by_village(query, score_cutoff=60):
    # fuzzy match so small spelling mistakes still work
    from rapidfuzz import process, fuzz

    all_phcs = get_all_phcs_with_status()
    names = [p["village_name"] for p in all_phcs]

    match = process.extractOne(query, names, scorer=fuzz.WRatio, score_cutoff=score_cutoff)
    if match is None:
        return None

    _name, score, index = match
    result = all_phcs[index]
    result["confidence"] = round(score, 1)
    return result
