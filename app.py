import streamlit as st
import pandas as pd
import plotly.express as px

import database as db

from datetime import date, timedelta, datetime

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

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


def previous_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


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


def build_master_register(register_venue, register_year, register_month, show_inactive=False):
    register_month_start, register_month_end = month_range(register_year, register_month)
    class_dates = get_class_dates_for_month(register_venue, register_year, register_month)

    players = db.get_players_for_month(
        register_venue,
        register_month_start,
        register_month_end,
        include_inactive=show_inactive
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
            "Leaving Date": leaving_date,
        }

        row = {
            "__player_id": player_id,
            "Delete Permanently": False,
            "Date Joined": joining_date,
            "Name": player_name,
            "Date of Birth": dob,
            "Current Age": calculate_age(dob),
            "Venue": venue,
            "Status": status,
            "Leaving Date": leaving_date,
        }

        for class_item in class_dates:
            class_col = f"Class {class_item['class_no']} - {class_item['class_date'].strftime('%d-%m-%Y')}"
            row[class_col] = attendance_map.get(
                (player_id, class_item["class_date"].isoformat()),
                ""
            )

        editable_rows.append(row)

    # blank row for adding a new player
    blank_row = {
        "__player_id": None,
        "Delete Permanently": False,
        "Date Joined": register_month_start,
        "Name": "",
        "Date of Birth": None,
        "Current Age": None,
        "Venue": register_venue,
        "Status": "Active",
        "Leaving Date": None,
    }
    for class_item in class_dates:
        class_col = f"Class {class_item['class_no']} - {class_item['class_date'].strftime('%d-%m-%Y')}"
        blank_row[class_col] = ""

    editable_rows.append(blank_row)

    base_columns = [
        "__player_id",
        "Delete Permanently",
        "Date Joined",
        "Name",
        "Date of Birth",
        "Current Age",
        "Venue",
        "Status",
        "Leaving Date",
    ]

    attendance_columns = [
        f"Class {item['class_no']} - {item['class_date'].strftime('%d-%m-%Y')}"
        for item in class_dates
    ]

    all_columns = base_columns + attendance_columns
    register_df = pd.DataFrame(editable_rows, columns=all_columns)

    return register_df, original_rows, class_dates, register_month_start, register_month_end, attendance_columns


def get_player_options_for_coordinator(register_venue, register_year, register_month):
    month_start, month_end = month_range(register_year, register_month)
    players = db.get_players_for_month(
        register_venue,
        month_start,
        month_end,
        include_inactive=False
    )
    return players, month_start, month_end


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
            index=summary_year_options.index(default_summary_year)
        )

    summary_month_options = get_season_month_options(summary_season_start_year)

    with summary_mid:
        selected_summary_months = st.multiselect(
            "Months",
            summary_month_options,
            default=summary_month_options
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

    master_df, original_rows, class_dates, admin_month_start, admin_month_end, attendance_columns = build_master_register(
        admin_venue,
        admin_year,
        admin_month,
        show_inactive=show_inactive_admin
    )

    base_columns = [
        "__player_id",
        "Delete Permanently",
        "Date Joined",
        "Name",
        "Date of Birth",
        "Current Age",
        "Venue",
        "Status",
        "Leaving Date",
    ]

    column_config = {
        "__player_id": None,
        "Delete Permanently": st.column_config.CheckboxColumn("Delete Permanently"),
        "Date Joined": st.column_config.DateColumn("Date Joined", format="DD-MM-YYYY"),
        "Name": st.column_config.TextColumn("Name"),
        "Date of Birth": st.column_config.DateColumn("Date of Birth", format="DD-MM-YYYY"),
        "Current Age": st.column_config.NumberColumn("Current Age", disabled=True),
        "Venue": st.column_config.SelectboxColumn("Venue", options=VENUES),
        "Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS),
        "Leaving Date": st.column_config.DateColumn("Leaving Date", format="DD-MM-YYYY"),
    }

    for col in attendance_columns:
        column_config[col] = st.column_config.SelectboxColumn(
            col,
            options=ATTENDANCE_OPTIONS,
            help="✓ = Present, ✕ = Absent"
        )

    attendance_style = JsCode(
        """
        function(params) {
            if (params.value === '✓') {
                return {'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': '600'};
            }
            if (params.value === '✕') {
                return {'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': '600'};
            }
            return {'backgroundColor': '#ffffff'};
        }
        """
    )

    gb = GridOptionsBuilder.from_dataframe(master_df)
    gb.configure_default_column(editable=False, resizable=True, sortable=False, filter=False)
    gb.configure_column("__player_id", hide=True)
    gb.configure_column("Delete Permanently", editable=True, pinned="left", width=140)
    gb.configure_column("Date Joined", editable=True, pinned="left", width=120)
    gb.configure_column("Name", editable=True, pinned="left", width=180)
    gb.configure_column("Date of Birth", editable=True, pinned="left", width=120)
    gb.configure_column("Current Age", editable=False, pinned="left", width=100)
    gb.configure_column("Venue", editable=True, pinned="left", width=150)
    gb.configure_column("Status", editable=True, pinned="left", width=110)
    gb.configure_column("Leaving Date", editable=True, pinned="left", width=120)

    for col in attendance_columns:
        gb.configure_column(
            col,
            editable=True,
            cellEditor="agSelectCellEditor",
            cellEditorParams={"values": ATTENDANCE_OPTIONS},
            cellStyle=attendance_style,
            width=120
        )

    grid_options = gb.build()

    st.caption("Tip: tick Delete Permanently and click Save Admin Sheet to remove a player card fully.")

    grid_response = AgGrid(
        master_df,
        grid_options,
        height=760,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        theme="streamlit",
        reload_data=True,
        key=f"admin_grid_{admin_venue}_{admin_year}_{admin_month}_{int(show_inactive_admin)}"
    )

    edited_master_df = grid_response.data
    if not isinstance(edited_master_df, pd.DataFrame):
        edited_master_df = pd.DataFrame(edited_master_df)

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

            delete_flag = bool(row.get("Delete Permanently", False))

            if delete_flag and existing_player_id is not None:
                db.delete_player_permanently(existing_player_id)
                continue

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

            status_to_save = safe_text(row.get("Status", "Active")) or original.get("Status") or "Active"
            if status_to_save not in STATUS_OPTIONS:
                status_to_save = "Active"

            leaving_date = to_date_value(row.get("Leaving Date"))
            if status_to_save == "Left" and leaving_date is None:
                leaving_date = admin_month_end
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
                class_col = f"{class_item['class_no']}. {class_item['class_date'].strftime('%d-%m-%Y')}"
                if class_col not in row:
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
            f"Use this on mobile. Select one player and mark only attendance. "
            f"Schedule: {VENUE_SCHEDULES[coord_venue]['display']}"
        )

    players_for_month, _, _ = get_player_options_for_coordinator(coord_venue, coord_year, coord_month)

    if not players_for_month:
        st.warning("No active players found for this venue/month.")
    else:
        player_map = {p[1]: p for p in players_for_month}
        player_names = list(player_map.keys())

        selected_player_name = st.selectbox(
            "Player",
            player_names,
            key="coord_player_name"
        )

        selected_player = player_map[selected_player_name]
        selected_player_id = selected_player[0]
        selected_player_dob = to_date_value(selected_player[2])
        selected_player_status = selected_player[4]
        selected_player_joined = to_date_value(selected_player[5])
        selected_player_leaving = to_date_value(selected_player[6])

        attendance_records_month = db.get_attendance_for_venue_month(
            coord_venue,
            coord_month_start,
            coord_month_end
        )

        player_attendance_map = {}
        for record in attendance_records_month:
            if int(record[0]) == int(selected_player_id):
                player_attendance_map[record[1]] = db_status_to_ui(record[2])

        st.markdown("### Player Snapshot")
        snap1, snap2 = st.columns(2)
        with snap1:
            st.write(f"**Date Joined:** {selected_player_joined.strftime('%d-%m-%Y') if selected_player_joined else '-'}")
            st.write(f"**Date of Birth:** {selected_player_dob.strftime('%d-%m-%Y') if selected_player_dob else '-'}")
        with snap2:
            st.write(f"**Current Age:** {calculate_age(selected_player_dob) if selected_player_dob else '-'}")
            st.write(f"**Status:** {selected_player_status}")

        with st.form("coordinator_form"):
            st.markdown("### Mark Attendance")
            st.caption("Tick = Present, X = Absent")

            attendance_values = {}
            for class_item in coord_class_dates:
                class_label = f"{class_item['class_no']}. {class_item['class_date'].strftime('%d-%m-%Y')}"
                current_value = player_attendance_map.get(class_item["class_date"].isoformat(), "")

                row_left, row_right = st.columns([4, 1])
                with row_left:
                    st.markdown(
                        f"<span style='color:#1f77b4; font-weight:600;'>{class_label}</span>",
                        unsafe_allow_html=True
                    )
                with row_right:
                    attendance_values[class_item["class_date"].isoformat()] = st.selectbox(
                        " ",
                        ATTENDANCE_OPTIONS,
                        index=ATTENDANCE_OPTIONS.index(current_value) if current_value in ATTENDANCE_OPTIONS else 0,
                        key=f"coord_att_{selected_player_id}_{class_item['class_no']}",
                        label_visibility="collapsed"
                    )

            save_attendance_clicked = st.form_submit_button("Save Attendance", type="primary")

        if save_attendance_clicked:
            for class_item in coord_class_dates:
                class_date_iso = class_item["class_date"].isoformat()
                ui_val = attendance_values.get(class_date_iso, "")
                db_val = ui_status_to_db(ui_val)

                if db_val == "":
                    db.delete_attendance(selected_player_id, class_date_iso)
                else:
                    db.save_attendance(
                        selected_player_id,
                        selected_player_name,
                        class_date_iso,
                        coord_venue,
                        db_val
                    )

            st.success(f"Attendance saved for {selected_player_name}")
            st.rerun()