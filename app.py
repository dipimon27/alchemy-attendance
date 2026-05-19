import streamlit as st
import pandas as pd
import plotly.express as px

import database as db

from datetime import date, timedelta, datetime

st.set_page_config(
    page_title="Alchemy Football Academy",
    layout="wide"
)

db.create_tables()

VENUES = [
    "Sports Drome",
    "Play Arena",
    "ECC",
    "Match Point",
    "CSE",
    "Powerplay Weekend",
    "Powerplay Juniors"
]

STATUS_OPTIONS = [
    "Active",
    "Pause",
    "Left"
]

ATTENDANCE_OPTIONS = [
    "",
    "✓",
    "✕"
]

VENUE_SCHEDULES = {
    "Sports Drome": {
        "days": [5, 6],
        "display": "Sat, Sun | 3:00 PM - 5:00 PM"
    },
    "Play Arena": {
        "days": [3, 4],
        "display": "Thu, Fri | 5:00 PM - 6:30 PM"
    },
    "ECC": {
        "days": [0, 2, 5, 6],
        "display": "Mon, Wed | 5:00 PM - 6:30 PM; Sat, Sun | 8:00 AM - 9:30 AM"
    },
    "Match Point": {
        "days": [5, 6],
        "display": "Sat, Sun | 3:30 PM - 5:00 PM"
    },
    "CSE": {
        "days": [5, 6],
        "display": "Sat, Sun | 4:00 PM - 5:30 PM"
    },
    "Powerplay Weekend": {
        "days": [5, 6],
        "display": "Sat 4:00 PM - 5:30 PM | Sun 10:00 AM - 11:30 AM"
    },
    "Powerplay Juniors": {
        "days": [5, 6],
        "display": "Sat, Sun | 8:30 AM - 10:00 AM"
    }
}


def month_label(year, month):
    return date(year, month, 1).strftime("%B %Y")


def get_playing_season_months(start_year):
    months = []
    for month in range(4, 13):
        months.append((start_year, month))
    for month in range(1, 4):
        months.append((start_year + 1, month))
    return months


def get_season_month_options(start_year):
    return [month_label(y, m) for y, m in get_playing_season_months(start_year)]


def month_range(year, month):
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year, 12, 31)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    return start_date, end_date


def get_playing_season_bounds(selected_date):
    if selected_date.month >= 4:
        season_start = date(selected_date.year, 4, 1)
        season_end = date(selected_date.year + 1, 3, 31)
        season_label = f"{selected_date.year}-{selected_date.year + 1}"
    else:
        season_start = date(selected_date.year - 1, 4, 1)
        season_end = date(selected_date.year, 3, 31)
        season_label = f"{selected_date.year - 1}-{selected_date.year}"
    return season_start, season_end, season_label


def get_class_dates_for_month(venue, year, month):
    if venue not in VENUE_SCHEDULES:
        return []

    schedule = VENUE_SCHEDULES[venue]
    month_start, month_end = month_range(year, month)

    class_dates = []
    current_date = month_start
    class_no = 0

    while current_date <= month_end:
        if current_date.weekday() in schedule["days"]:
            class_no += 1
            class_dates.append({
                "class_no": class_no,
                "class_date": current_date
            })
        current_date += timedelta(days=1)

    return class_dates


def db_status_to_ui(status):
    if status == "Present":
        return "✓"
    if status == "Absent":
        return "✕"
    return ""


def ui_status_to_db(status):
    if status == "✓":
        return "Present"
    if status == "✕":
        return "Absent"
    return ""


def to_date_value(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value)
        except Exception:
            try:
                return datetime.strptime(value, "%d-%m-%Y").date()
            except Exception:
                return None
    return None


def safe_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def render_metric_card(label, value, sublabel=None):
    st.markdown(
        f"""
        <div style="
            padding: 18px;
            border-radius: 14px;
            background-color: #f8f9fa;
            border: 1px solid #e6e6e6;
            min-height: 110px;
        ">
            <div style="font-size: 14px; color: #666; margin-bottom: 8px;">{label}</div>
            <div style="font-size: 30px; font-weight: 700; color: #111;">{value}</div>
            <div style="font-size: 12px; color: #777; margin-top: 6px;">{sublabel or ""}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.title("Alchemy International Football Academy")
st.caption("Attendance tracker for the playing season from 1 April to 31 March.")

tabs = st.tabs(["Summary", "Attendance Register"])


with tabs[0]:
    st.header("Summary Dashboard")

    summary_left, summary_mid, summary_right = st.columns([1, 1.5, 1])

    summary_year_options = list(range(date.today().year - 2, date.today().year + 3))
    default_summary_year = date.today().year if date.today().month >= 4 else date.today().year - 1

    with summary_left:
        summary_season_start_year = st.selectbox(
            "Season start year",
            summary_year_options,
            index=summary_year_options.index(default_summary_year)
        )

    summary_month_options = get_season_month_options(summary_season_start_year)

    with summary_mid:
        selected_summary_months = st.multiselect(
            "Months",
            summary_month_options,
            default=summary_month_options
        )

    selected_pairs = get_playing_season_months(summary_season_start_year)
    selected_pair_set = set(selected_summary_months)

    matching_pairs = [(y, m) for (y, m) in selected_pairs if month_label(y, m) in selected_pair_set]

    if matching_pairs:
        first_y, first_m = matching_pairs[0]
        last_y, last_m = matching_pairs[-1]
        summary_period_start = month_range(first_y, first_m)[0]
        summary_period_end = month_range(last_y, last_m)[1]
    else:
        summary_period_start = date(summary_season_start_year, 4, 1)
        summary_period_end = date(summary_season_start_year + 1, 3, 31)

    with summary_right:
        st.info(
            f"Summary period: {summary_period_start.strftime('%d-%m-%Y')} to {summary_period_end.strftime('%d-%m-%Y')}"
        )

    active_players_count = db.get_active_player_count_as_of(summary_period_end)

    attendance_records = db.get_attendance_records_between(summary_period_start, summary_period_end)

    present_count = 0
    absent_count = 0
    selected_months_set = set(selected_summary_months)

    for rec in attendance_records:
        class_date = to_date_value(rec[2])
        if class_date is None:
            continue

        label = month_label(class_date.year, class_date.month)
        if label not in selected_months_set:
            continue

        if rec[4] == "Present":
            present_count += 1
        elif rec[4] == "Absent":
            absent_count += 1

    attendance_rate = 0
    if present_count + absent_count > 0:
        attendance_rate = round((present_count / (present_count + absent_count)) * 100, 1)

    cards = st.columns(2)
    with cards[0]:
        render_metric_card(
            "Active Players",
            active_players_count,
            f"As of {summary_period_end.strftime('%d-%m-%Y')}"
        )
    with cards[1]:
        render_metric_card(
            "Attendance Rate",
            f"{attendance_rate}%",
            f"Present: {present_count} | Absent: {absent_count}"
        )

    st.markdown("### Active Players Month by Month")
    monthly_counts = db.get_monthly_active_player_counts(summary_season_start_year)
    monthly_df = pd.DataFrame(monthly_counts)

    if not monthly_df.empty:
        fig_line = px.line(
            monthly_df,
            x="month",
            y="active_players",
            markers=True
        )
        fig_line.update_layout(
            xaxis_title="",
            yaxis_title="Active Players"
        )
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("### Active Players by Venue")
    venue_rows = db.get_active_players_by_venue_as_of(summary_period_end)
    venue_df = pd.DataFrame(venue_rows, columns=["Venue", "Active Players"])

    if not venue_df.empty:
        fig_bar = px.bar(
            venue_df,
            x="Venue",
            y="Active Players",
            color="Venue",
            text="Active Players"
        )
        fig_bar.update_layout(
            xaxis_title="",
            yaxis_title="Active Players",
            showlegend=True
        )
        st.plotly_chart(fig_bar, use_container_width=True)


with tabs[1]:
    st.header("Attendance Register")

    reg_left, reg_mid, reg_right = st.columns(3)

    with reg_left:
        register_venue = st.selectbox("Venue", VENUES)

    with reg_mid:
        register_year = st.selectbox(
            "Year",
            list(range(date.today().year - 2, date.today().year + 3)),
            index=list(range(date.today().year - 2, date.today().year + 3)).index(date.today().year)
        )

    with reg_right:
        register_month = st.selectbox(
            "Month",
            list(range(1, 13)),
            format_func=lambda m: date(2000, m, 1).strftime("%B"),
            index=date.today().month - 1
        )

    register_month_start, register_month_end = month_range(register_year, register_month)
    register_label = month_label(register_year, register_month)

    st.caption(
        f"Register month: {register_label} | {register_month_start.strftime('%d-%m-%Y')} to {register_month_end.strftime('%d-%m-%Y')}"
    )

    venue_schedule = VENUE_SCHEDULES.get(register_venue, {})
    if venue_schedule:
        st.info(
            f"Blue columns are attendance columns. Only those should be filled by coordinators. "
            f"Use ✓ for present and ✕ for absent. Schedule: {venue_schedule['display']}"
        )

    class_dates = get_class_dates_for_month(register_venue, register_year, register_month)

    players = db.get_players_for_month(
        register_venue,
        register_month_start,
        register_month_end,
        include_inactive=False
    )

    attendance_records_month = db.get_attendance_for_venue_month(
        register_venue,
        register_month_start,
        register_month_end
    )

    attendance_map = {}
    for record in attendance_records_month:
        player_id = record[0]
        saved_date = record[1]
        saved_status = record[2]
        attendance_map[(player_id, saved_date)] = db_status_to_ui(saved_status)

    register_cards = st.columns(2)
    active_players_in_register = sum(1 for p in players if p[4] == "Active")

    present_count_reg = 0
    absent_count_reg = 0
    for rec in attendance_records_month:
        if rec[2] == "Present":
            present_count_reg += 1
        elif rec[2] == "Absent":
            absent_count_reg += 1

    register_attendance_rate = 0
    if present_count_reg + absent_count_reg > 0:
        register_attendance_rate = round((present_count_reg / (present_count_reg + absent_count_reg)) * 100, 1)

    with register_cards[0]:
        render_metric_card(
            "Active Players",
            active_players_in_register,
            f"{register_venue} | {register_label}"
        )

    with register_cards[1]:
        render_metric_card(
            "Attendance Rate",
            f"{register_attendance_rate}%",
            f"Present: {present_count_reg} | Absent: {absent_count_reg}"
        )

    editable_rows = []
    original_rows = {}

    for player in players:
        player_id = player[0]
        player_name = player[1]
        dob = to_date_value(player[2])
        venue = player[3]
        status = player[4]
        joining_date = to_date_value(player[5])
        leaving_date = to_date_value(player[6])

        original_rows[player_id] = {
            "Name": player_name,
            "Date of Birth": dob,
            "Venue": venue,
            "Status": status,
            "Date Joined": joining_date,
            "Leaving Date": leaving_date
        }

        row = {
            "Player ID": player_id,
            "Delete Permanently": False,
            "Date Joined": joining_date,
            "Name": player_name,
            "Date of Birth": dob,
            "Venue": venue,
            "Status": status,
            "Leaving Date": leaving_date
        }

        for class_item in class_dates:
            class_col = f"🟦 Class {class_item['class_no']} - {class_item['class_date'].strftime('%d-%m-%Y')}"
            row[class_col] = attendance_map.get(
                (player_id, class_item["class_date"].isoformat()),
                ""
            )

        editable_rows.append(row)

    base_columns = [
        "Player ID",
        "Delete Permanently",
        "Date Joined",
        "Name",
        "Date of Birth",
        "Venue",
        "Status",
        "Leaving Date"
    ]

    attendance_columns = [
        f"🟦 Class {item['class_no']} - {item['class_date'].strftime('%d-%m-%Y')}"
        for item in class_dates
    ]

    all_columns = base_columns + attendance_columns
    register_df = pd.DataFrame(editable_rows, columns=all_columns)

    column_config = {
        "Player ID": st.column_config.NumberColumn("Player ID", disabled=True),
        "Delete Permanently": st.column_config.CheckboxColumn("Delete Permanently"),
        "Date Joined": st.column_config.DateColumn("Date Joined", format="DD-MM-YYYY"),
        "Name": st.column_config.TextColumn("Name"),
        "Date of Birth": st.column_config.DateColumn("Date of Birth", format="DD-MM-YYYY"),
        "Venue": st.column_config.SelectboxColumn("Venue", options=VENUES),
        "Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS),
        "Leaving Date": st.column_config.DateColumn("Leaving Date", format="DD-MM-YYYY")
    }

    for col in attendance_columns:
        column_config[col] = st.column_config.SelectboxColumn(
            col,
            options=ATTENDANCE_OPTIONS,
            help="Blue attendance column: ✓ present, ✕ absent"
        )

    edited_df = st.data_editor(
        register_df,
        use_container_width=True,
        hide_index=True,
        height=760,
        num_rows="dynamic",
        column_config=column_config,
        column_order=base_columns + attendance_columns,
        disabled=["Player ID"]
    )

    if st.button("Save Register", type="primary"):
        for _, row in edited_df.iterrows():
            raw_player_id = row.get("Player ID", None)
            player_name = safe_text(row.get("Name", ""))

            existing_player_id = None
            if raw_player_id is not None and not pd.isna(raw_player_id):
                try:
                    existing_player_id = int(raw_player_id)
                except Exception:
                    existing_player_id = None

            delete_flag = bool(row.get("Delete Permanently", False))

            if delete_flag and existing_player_id is not None:
                db.delete_player_permanently(existing_player_id)
                continue

            # Skip totally blank new rows
            if existing_player_id is None and player_name == "":
                continue

            original = original_rows.get(existing_player_id, {}) if existing_player_id is not None else {}

            joined_date = to_date_value(row.get("Date Joined"))
            if joined_date is None:
                joined_date = original.get("Date Joined") or register_month_start

            dob = to_date_value(row.get("Date of Birth"))
            if dob is None and existing_player_id is not None:
                dob = original.get("Date of Birth")

            venue_to_save = safe_text(row.get("Venue", register_venue)) or original.get("Venue") or register_venue
            if venue_to_save not in VENUES:
                venue_to_save = register_venue

            status_to_save = safe_text(row.get("Status", "Active")) or original.get("Status") or "Active"
            if status_to_save not in STATUS_OPTIONS:
                status_to_save = "Active"

            leaving_date = to_date_value(row.get("Leaving Date"))
            if status_to_save == "Left" and leaving_date is None:
                leaving_date = register_month_end
            if status_to_save != "Left":
                leaving_date = None

            if existing_player_id is None:
                player_id_to_use = db.add_player(
                    player_name,
                    dob,
                    venue_to_save,
                    status_to_save,
                    joined_date,
                    leaving_date
                )
            else:
                db.update_player(
                    existing_player_id,
                    player_name if player_name else original.get("Name", ""),
                    dob,
                    venue_to_save,
                    status_to_save,
                    joined_date,
                    leaving_date
                )
                player_id_to_use = existing_player_id

            for class_item in class_dates:
                class_col = f"🟦 Class {class_item['class_no']} - {class_item['class_date'].strftime('%d-%m-%Y')}"
                ui_val = safe_text(row.get(class_col, ""))

                db_val = ui_status_to_db(ui_val)

                if db_val == "":
                    db.delete_attendance(player_id_to_use, class_item["class_date"].isoformat())
                else:
                    db.save_attendance(
                        player_id_to_use,
                        player_name if player_name else original.get("Name", ""),
                        class_item["class_date"].isoformat(),
                        venue_to_save,
                        db_val
                    )

        st.success("Register saved")
        st.rerun()