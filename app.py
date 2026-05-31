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
    "Powerplay Seniors",
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
    "Powerplay Seniors": {
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


def calculate_age(dob):
    if dob is None:
        return None

    today = date.today()
    years = today.year - dob.year

    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1

    return years


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


def get_summary_period(year_start, selected_summary_months):
    selected_pairs = get_playing_season_months(year_start)
    selected_pair_set = set(selected_summary_months)
    matching_pairs = [(y, m) for (y, m) in selected_pairs if month_label(y, m) in selected_pair_set]

    if matching_pairs:
        first_y, first_m = matching_pairs[0]
        last_y, last_m = matching_pairs[-1]
        summary_period_start = month_range(first_y, first_m)[0]
        summary_period_end = month_range(last_y, last_m)[1]
    else:
        summary_period_start = date(year_start, 4, 1)
        summary_period_end = date(year_start + 1, 3, 31)

    return summary_period_start, summary_period_end


def build_admin_register(admin_venue, admin_year, admin_month, show_inactive=False):
    month_start, month_end = month_range(admin_year, admin_month)
    class_dates = get_class_dates_for_month(admin_venue, admin_year, admin_month)

    players = db.get_players_for_month(
        admin_venue,
        month_start,
        month_end,
        include_inactive=show_inactive
    )

    attendance_records = db.get_attendance_for_venue_month(
        admin_venue,
        month_start,
        month_end
    )

    attendance_map = {}
    for record in attendance_records:
        player_id = record[0]
        saved_date = record[1]
        saved_status = record[2]
        attendance_map[(player_id, saved_date)] = db_status_to_ui(saved_status)

    rows = []
    original_rows = {}

    for player in players:
        player_id = player[0]
        player_name = player[1]
        dob = to_date_value(player[2])
        venue = player[3]
        fees_paid = player[4]
        status = player[5]
        joining_date = to_date_value(player[6])
        leaving_date = to_date_value(player[7])

        original_rows[player_id] = {
            "Name": player_name,
            "Date of Birth": dob,
            "Venue": venue,
            "Fees Paid": fees_paid,
            "Status": status,
            "Date Joined": joining_date,
            "Leaving Date": leaving_date,
        }

        row = {
            "__player_id": player_id,
            "Date Joined": joining_date,
            "Name": player_name,
            "Date of Birth": dob,
            "Current Age": calculate_age(dob),
            "Venue": venue,
            "Fees Paid": fees_paid,
            "Status": status,
        }

        for class_item in class_dates:
            class_col = f"Class {class_item['class_no']} - {class_item['class_date'].strftime('%d-%m-%Y')}"
            row[class_col] = attendance_map.get(
                (player_id, class_item["class_date"].isoformat()),
                ""
            )

        rows.append(row)

    # blank row for adding a new player
    blank_row = {
        "__player_id": None,
        "Date Joined": month_start,
        "Name": "",
        "Date of Birth": None,
        "Current Age": None,
        "Venue": admin_venue,
        "Fees Paid": "",
        "Status": "Active",
    }

    for class_item in class_dates:
        class_col = f"Class {class_item['class_no']} - {class_item['class_date'].strftime('%d-%m-%Y')}"
        blank_row[class_col] = ""

    rows.append(blank_row)

    base_columns = [
        "__player_id",
        "Date Joined",
        "Name",
        "Date of Birth",
        "Current Age",
        "Venue",
        "Fees Paid",
        "Status",
    ]

    attendance_columns = [
        f"Class {item['class_no']} - {item['class_date'].strftime('%d-%m-%Y')}"
        for item in class_dates
    ]

    register_df = pd.DataFrame(rows, columns=base_columns + attendance_columns)
    return register_df, original_rows, class_dates, month_start, month_end, attendance_columns


st.title("Alchemy International Football Academy")
st.caption("Attendance tracker for the playing season from 1 April to 31 March.")

tabs = st.tabs(["Summary", "Admin Review Sheet", "Coordinator Register"])


with tabs[0]:
    st.header("Summary Dashboard")

    summary_left, summary_mid, summary_right = st.columns([1, 1.5, 1])

    summary_year_options = list(range(date.today().year - 2, date.today().year + 3))
    default_summary_year = date.today().year if date.today().month >= 4 else date.today().year - 1

    with summary_left:
        summary_season_start_year = st.selectbox(
            "Season start year",
            summary_year_options,
            index=summary_year_options.index(default_summary_year),
            key="summary_year"
        )

    summary_month_options = get_season_month_options(summary_season_start_year)

    with summary_mid:
        selected_summary_months = st.multiselect(
            "Months",
            summary_month_options,
            default=summary_month_options,
            key="summary_months"
        )

    summary_period_start, summary_period_end = get_summary_period(
        summary_season_start_year,
        selected_summary_months
    )

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
        fig_line.update_layout(xaxis_title="", yaxis_title="Active Players")
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
    st.header("Admin Review Sheet")

    admin_left, admin_mid, admin_right = st.columns(3)

    with admin_left:
        admin_venue = st.selectbox("Venue", VENUES, key="admin_venue")

    with admin_mid:
        admin_year = st.selectbox(
            "Year",
            list(range(date.today().year - 2, date.today().year + 3)),
            index=list(range(date.today().year - 2, date.today().year + 3)).index(date.today().year),
            key="admin_year"
        )

    with admin_right:
        admin_month = st.selectbox(
            "Month",
            list(range(1, 13)),
            format_func=lambda m: date(2000, m, 1).strftime("%B"),
            index=date.today().month - 1,
            key="admin_month"
        )

    show_inactive_admin = st.checkbox("Show inactive players", value=False, key="show_inactive_admin")

    admin_month_start, admin_month_end = month_range(admin_year, admin_month)

    st.caption(
        f"Admin month: {month_label(admin_year, admin_month)} | "
        f"{admin_month_start.strftime('%d-%m-%Y')} to {admin_month_end.strftime('%d-%m-%Y')}"
    )

    if admin_venue in VENUE_SCHEDULES:
        st.info(f"Class pattern: {VENUE_SCHEDULES[admin_venue]['display']}")

    st.markdown("#### Add player")
    with st.form("add_player_form"):
        add_cols = st.columns(6)

        with add_cols[0]:
            new_name = st.text_input("Name")
        with add_cols[1]:
            new_dob = st.date_input(
                "Date of Birth",
                value=date(2016, 1, 1),
                min_value=date(2000, 1, 1),
                max_value=date.today()
            )
        with add_cols[2]:
            new_joined = st.date_input(
                "Date Joined",
                value=admin_month_start,
                min_value=date(2000, 1, 1),
                max_value=date.today()
            )
        with add_cols[3]:
            new_venue = st.selectbox("Venue", VENUES, index=VENUES.index(admin_venue))
        with add_cols[4]:
            new_fees_paid = st.text_input("Fees Paid")
        with add_cols[5]:
            new_status = st.selectbox("Status", STATUS_OPTIONS, index=0)

        add_submit = st.form_submit_button("Add Player")

        if add_submit:
            if not new_name.strip():
                st.error("Name is required.")
            else:
                leaving_date = None
                if new_status == "Left":
                    leaving_date = new_joined

                db.add_player(
                    new_name.strip(),
                    new_dob,
                    new_venue,
                    new_fees_paid,
                    new_status,
                    new_joined,
                    leaving_date
                )
                st.success(f"{new_name} added")
                st.rerun()

    register_df, original_rows, class_dates, admin_month_start, admin_month_end, attendance_columns = build_admin_register(
        admin_venue,
        admin_year,
        admin_month,
        show_inactive=show_inactive_admin
    )

    delete_options = []
    delete_map = {}

    for _, row in register_df.iterrows():
        pid = row["__player_id"]
        name = safe_text(row["Name"])
        if pd.isna(pid) or name == "":
            continue
        label = f"{int(pid)} | {name}"
        delete_options.append(label)
        delete_map[label] = int(pid)

    if delete_options:
        st.markdown("#### Delete player")
        del_left, del_right = st.columns([3, 1])

        with del_left:
            delete_choice = st.selectbox("Select player", delete_options, key="delete_choice")

        with del_right:
            st.write("")
            st.write("")
            delete_clicked = st.button("Delete Permanently", type="secondary")

        if delete_clicked:
            db.delete_player_permanently(delete_map[delete_choice])
            st.success("Player deleted")
            st.rerun()

    base_columns = [
        "__player_id",
        "Date Joined",
        "Name",
        "Date of Birth",
        "Current Age",
        "Venue",
        "Fees Paid",
        "Status",
    ]

    column_config = {
        "__player_id": None,
        "Date Joined": st.column_config.DateColumn(
            "Date Joined",
            format="DD-MM-YYYY",
            min_value=date(2000, 1, 1),
            max_value=date.today()
        ),
        "Name": st.column_config.TextColumn("Name"),
        "Date of Birth": st.column_config.DateColumn(
            "Date of Birth",
            format="DD-MM-YYYY",
            min_value=date(2000, 1, 1),
            max_value=date.today()
        ),
        "Current Age": st.column_config.NumberColumn("Current Age", disabled=True),
        "Venue": st.column_config.SelectboxColumn("Venue", options=VENUES),
        "Fees Paid": st.column_config.TextColumn("Fees Paid"),
        "Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS),
    }

    for col in attendance_columns:
        column_config[col] = st.column_config.SelectboxColumn(
            col,
            options=ATTENDANCE_OPTIONS,
            help="✓ = Present, ✕ = Absent"
        )

    st.caption("Edit master details here. Attendance changes made here will mirror in the coordinator register.")

    edited_master_df = st.data_editor(
        register_df,
        use_container_width=True,
        hide_index=True,
        height=760,
        num_rows="fixed",
        column_config=column_config,
        column_order=base_columns + attendance_columns,
        disabled=["Current Age"]
    )

    if st.button("Save Admin Sheet", type="primary"):
        for _, row in edited_master_df.iterrows():
            raw_player_id = row.get("__player_id", None)
            player_name = safe_text(row.get("Name", ""))

            existing_player_id = None
            if raw_player_id is not None and not pd.isna(raw_player_id):
                try:
                    existing_player_id = int(raw_player_id)
                except Exception:
                    existing_player_id = None

            if existing_player_id is None and player_name == "":
                continue

            original = original_rows.get(existing_player_id, {}) if existing_player_id is not None else {}

            joined_date = to_date_value(row.get("Date Joined"))
            if joined_date is None:
                joined_date = original.get("Date Joined") or admin_month_start

            dob = to_date_value(row.get("Date of Birth"))
            if dob is None and existing_player_id is not None:
                dob = original.get("Date of Birth")

            venue_to_save = safe_text(row.get("Venue", admin_venue)) or original.get("Venue") or admin_venue
            if venue_to_save not in VENUES:
                venue_to_save = admin_venue

            fees_paid_to_save = safe_text(row.get("Fees Paid", ""))
            if fees_paid_to_save == "" and existing_player_id is not None:
                fees_paid_to_save = safe_text(original.get("Fees Paid", ""))

            status_to_save = safe_text(row.get("Status", "Active")) or original.get("Status") or "Active"
            if status_to_save not in STATUS_OPTIONS:
                status_to_save = "Active"

            leaving_date = original.get("Leaving Date")
            if status_to_save == "Left":
                leaving_date = admin_month_end
            else:
                leaving_date = None

            if existing_player_id is None:
                player_id_to_use = db.add_player(
                    player_name,
                    dob,
                    venue_to_save,
                    fees_paid_to_save,
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
                    fees_paid_to_save,
                    status_to_save,
                    joined_date,
                    leaving_date
                )
                player_id_to_use = existing_player_id

            for class_item in class_dates:
                class_col = f"Class {class_item['class_no']} - {class_item['class_date'].strftime('%d-%m-%Y')}"
                ui_val = safe_text(row.get(class_col, ""))
                db_val = ui_status_to_db(ui_val)

                if db_val == "":
                    db.delete_attendance(player_id_to_use, class_item["class_date"].isoformat())
                else:
                    db.save_attendance(
                        player_id_to_use,
                        player_name,
                        class_item["class_date"].isoformat(),
                        venue_to_save,
                        db_val
                    )

        st.success("Admin sheet saved")
        st.rerun()


with tabs[2]:
    st.header("Coordinator Register")

    coord_left, coord_mid, coord_right = st.columns(3)

    with coord_left:
        coord_venue = st.selectbox("Venue", VENUES, key="coord_venue")

    with coord_mid:
        coord_year = st.selectbox(
            "Year",
            list(range(date.today().year - 2, date.today().year + 3)),
            index=list(range(date.today().year - 2, date.today().year + 3)).index(date.today().year),
            key="coord_year"
        )

    with coord_right:
        coord_month = st.selectbox(
            "Month",
            list(range(1, 13)),
            format_func=lambda m: date(2000, m, 1).strftime("%B"),
            index=date.today().month - 1,
            key="coord_month"
        )

    coord_month_start, coord_month_end = month_range(coord_year, coord_month)
    coord_class_dates = get_class_dates_for_month(coord_venue, coord_year, coord_month)

    st.caption(
        f"Coordinator month: {month_label(coord_year, coord_month)} | "
        f"{coord_month_start.strftime('%d-%m-%Y')} to {coord_month_end.strftime('%d-%m-%Y')}"
    )

    if coord_venue in VENUE_SCHEDULES:
        st.info(
            f"Use this view on mobile. Pick one class date, then mark players present or absent. "
            f"Schedule: {VENUE_SCHEDULES[coord_venue]['display']}"
        )

    if not coord_class_dates:
        st.warning("No class dates found for this venue and month.")
    else:
        class_options = {
            f"Class {item['class_no']} - {item['class_date'].strftime('%d-%m-%Y')}": item["class_date"]
            for item in coord_class_dates
        }

        selected_class_label = st.selectbox(
            "Class date",
            list(class_options.keys()),
            key="coord_class_date"
        )

        selected_class_date = class_options[selected_class_label]

        players_for_class = db.get_players_for_class(
            coord_venue,
            selected_class_date
        )

        if not players_for_class:
            st.warning("No active players found for this class date.")
        else:
            existing_attendance = db.get_attendance_for_class(
                coord_venue,
                selected_class_date
            )

            attendance_map = {
                int(row[0]): db_status_to_ui(row[1])
                for row in existing_attendance
            }

            st.markdown("### Players for selected class")
            st.caption("Mark each player with ✓ for present or ✕ for absent.")

            with st.form("coordinator_class_form"):
                attendance_values = {}

                for player in players_for_class:
                    player_id = int(player[0])
                    player_name = player[1]
                    dob = to_date_value(player[2])
                    fees_paid = safe_text(player[4])
                    status = player[5]
                    joined_date = to_date_value(player[6])

                    current_value = attendance_map.get(player_id, "")

                    row_left, row_right = st.columns([4, 1])
                    with row_left:
                        st.markdown(f"**{player_name}**")
                        st.caption(
                            f"Joined: {joined_date.strftime('%d-%m-%Y') if joined_date else '-'} | "
                            f"DOB: {dob.strftime('%d-%m-%Y') if dob else '-'} | "
                            f"Fees Paid: {fees_paid or '-'} | "
                            f"Status: {status}"
                        )

                    with row_right:
                        attendance_values[player_id] = st.selectbox(
                            "Attendance",
                            ATTENDANCE_OPTIONS,
                            index=ATTENDANCE_OPTIONS.index(current_value) if current_value in ATTENDANCE_OPTIONS else 0,
                            key=f"coord_att_{player_id}_{selected_class_date.isoformat()}",
                            label_visibility="collapsed"
                        )

                save_clicked = st.form_submit_button("Save Attendance", type="primary")

            if save_clicked:
                for player in players_for_class:
                    player_id = int(player[0])
                    player_name = player[1]

                    ui_val = attendance_values.get(player_id, "")
                    db_val = ui_status_to_db(ui_val)

                    if db_val == "":
                        db.delete_attendance(player_id, selected_class_date.isoformat())
                    else:
                        db.save_attendance(
                            player_id,
                            player_name,
                            selected_class_date.isoformat(),
                            coord_venue,
                            db_val
                        )

                st.success(f"Attendance saved for {selected_class_label}")
                st.rerun()