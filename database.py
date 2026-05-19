import sqlite3
from datetime import date, timedelta

DB_NAME = "alchemy_academy.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            dob TEXT,
            venue TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            joining_date TEXT,
            leaving_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            player_name TEXT,
            class_date TEXT NOT NULL,
            venue TEXT NOT NULL,
            attendance_status TEXT NOT NULL,
            UNIQUE(player_id, class_date)
        )
    """)

    conn.commit()
    conn.close()


def add_player(
    player_name,
    dob,
    venue,
    status,
    joining_date,
    leaving_date=None
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO players (
            player_name,
            dob,
            venue,
            status,
            joining_date,
            leaving_date
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        player_name,
        str(dob) if dob else None,
        venue,
        status,
        str(joining_date) if joining_date else None,
        str(leaving_date) if leaving_date else None
    ))

    player_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return player_id


def update_player(
    player_id,
    player_name,
    dob,
    venue,
    status,
    joining_date,
    leaving_date=None
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE players
        SET player_name = ?,
            dob = ?,
            venue = ?,
            status = ?,
            joining_date = ?,
            leaving_date = ?
        WHERE id = ?
    """, (
        player_name,
        str(dob) if dob else None,
        venue,
        status,
        str(joining_date) if joining_date else None,
        str(leaving_date) if leaving_date else None,
        int(player_id)
    ))

    conn.commit()
    conn.close()


def delete_player_permanently(player_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM attendance
        WHERE player_id = ?
    """, (int(player_id),))

    cursor.execute("""
        DELETE FROM players
        WHERE id = ?
    """, (int(player_id),))

    conn.commit()
    conn.close()


def get_players_for_month(venue, month_start, month_end, include_inactive=False):
    conn = get_connection()

    if include_inactive:
        query = """
            SELECT
                id,
                player_name,
                dob,
                venue,
                status,
                joining_date,
                leaving_date
            FROM players
            WHERE venue = ?
            ORDER BY status, player_name
        """
        params = (venue,)
    else:
        query = """
            SELECT
                id,
                player_name,
                dob,
                venue,
                status,
                joining_date,
                leaving_date
            FROM players
            WHERE venue = ?
              AND date(joining_date) <= date(?)
              AND (
                    leaving_date IS NULL
                    OR date(leaving_date) >= date(?)
              )
            ORDER BY status, player_name
        """
        params = (venue, month_end.isoformat(), month_start.isoformat())

    players = conn.execute(query, params).fetchall()
    conn.close()
    return players


def save_attendance(player_id, player_name, class_date, venue, attendance_status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO attendance (
            player_id,
            player_name,
            class_date,
            venue,
            attendance_status
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(player_id, class_date) DO UPDATE SET
            player_name = excluded.player_name,
            venue = excluded.venue,
            attendance_status = excluded.attendance_status
    """, (
        int(player_id),
        player_name,
        str(class_date),
        venue,
        attendance_status
    ))

    conn.commit()
    conn.close()


def delete_attendance(player_id, class_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM attendance
        WHERE player_id = ? AND class_date = ?
    """, (
        int(player_id),
        str(class_date)
    ))

    conn.commit()
    conn.close()


def get_attendance_for_venue_month(venue, month_start, month_end):
    conn = get_connection()

    query = """
        SELECT
            player_id,
            class_date,
            attendance_status
        FROM attendance
        WHERE venue = ?
          AND date(class_date) BETWEEN date(?) AND date(?)
    """

    records = conn.execute(
        query,
        (venue, month_start.isoformat(), month_end.isoformat())
    ).fetchall()

    conn.close()
    return records


def get_attendance_records_between(start_date, end_date):
    conn = get_connection()

    query = """
        SELECT
            player_id,
            player_name,
            class_date,
            venue,
            attendance_status
        FROM attendance
        WHERE date(class_date) BETWEEN date(?) AND date(?)
    """

    records = conn.execute(
        query,
        (start_date.isoformat(), end_date.isoformat())
    ).fetchall()

    conn.close()
    return records


def get_active_player_count_as_of(as_of_date):
    conn = get_connection()
    cursor = conn.cursor()

    count = cursor.execute("""
        SELECT COUNT(*)
        FROM players
        WHERE date(joining_date) <= date(?)
          AND (
                leaving_date IS NULL
                OR date(leaving_date) >= date(?)
          )
    """, (
        as_of_date.isoformat(),
        as_of_date.isoformat()
    )).fetchone()[0]

    conn.close()
    return count


def get_active_players_by_venue_as_of(as_of_date):
    conn = get_connection()
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT
            venue,
            COUNT(*)
        FROM players
        WHERE date(joining_date) <= date(?)
          AND (
                leaving_date IS NULL
                OR date(leaving_date) >= date(?)
          )
        GROUP BY venue
        ORDER BY venue
    """, (
        as_of_date.isoformat(),
        as_of_date.isoformat()
    )).fetchall()

    conn.close()
    return rows


def get_monthly_active_player_counts(season_start_year):
    conn = get_connection()
    cursor = conn.cursor()

    results = []

    # April to December
    for month in range(4, 13):
        month_start = date(season_start_year, month, 1)

        if month == 12:
            month_end = date(season_start_year, 12, 31)
        else:
            month_end = date(season_start_year, month + 1, 1) - timedelta(days=1)

        count = cursor.execute("""
            SELECT COUNT(*)
            FROM players
            WHERE date(joining_date) <= date(?)
              AND (
                    leaving_date IS NULL
                    OR date(leaving_date) >= date(?)
              )
        """, (
            month_end.isoformat(),
            month_end.isoformat()
        )).fetchone()[0]

        results.append({
            "month": month_start.strftime("%b %Y"),
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "active_players": count
        })

    # January to March of next year
    next_year = season_start_year + 1
    for month in range(1, 4):
        month_start = date(next_year, month, 1)

        if month == 3:
            month_end = date(next_year, 3, 31)
        else:
            month_end = date(next_year, month + 1, 1) - timedelta(days=1)

        count = cursor.execute("""
            SELECT COUNT(*)
            FROM players
            WHERE date(joining_date) <= date(?)
              AND (
                    leaving_date IS NULL
                    OR date(leaving_date) >= date(?)
              )
        """, (
            month_end.isoformat(),
            month_end.isoformat()
        )).fetchone()[0]

        results.append({
            "month": month_start.strftime("%b %Y"),
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "active_players": count
        })

    conn.close()
    return results