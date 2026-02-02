import os
import time
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# Page Setup
st.set_page_config(page_title="Minty Seeding Dashboard", page_icon="🌱", layout="wide")

st.title("🌱 Minty Seeding Watcher")
st.markdown("---")

SEED_DURATION_DAYS = 7
SEED_DURATION_SEC = SEED_DURATION_DAYS * 24 * 60 * 60
DOWNLOADS_PATH = "/home/martin/Downloads"


def format_countdown(seconds: int) -> str:
    """Format remaining seconds as D:HH:MM:SS or HH:MM:SS cleanly."""
    if seconds <= 0:
        return "00:00:00"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_seeding_status(directory: str) -> tuple[list[dict], int]:
    """
    Scan directory for files and calculate seeding status.
    Returns (files_data, skipped_dir_count).
    """
    files_data = []
    skipped_dirs = 0
    now = time.time()

    if not os.path.exists(directory):
        return [], 0

    for entry in os.listdir(directory):
        full_path = os.path.join(directory, entry)

        if os.path.isdir(full_path):
            skipped_dirs += 1
            continue

        if not os.path.isfile(full_path):
            continue

        mtime = os.path.getmtime(full_path)
        age = now - mtime
        remaining = SEED_DURATION_SEC - age
        is_safe = remaining <= 0

        files_data.append({
            "File": entry,
            "Status": "✅ Safe to Delete" if is_safe else "⏳ Seeding",
            "Time Remaining": "00:00:00" if is_safe else format_countdown(int(remaining)),
            "Added On": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
            "IsSafe": is_safe,
            # Store raw remaining for sorting (negative = already safe)
            "_remaining_sec": remaining,
        })

    return files_data, skipped_dirs


# --- Auto-refresh every 60 seconds ---
st.sidebar.header("Settings")
auto_refresh = st.sidebar.toggle("Auto-refresh (60s)", value=True)

# --- Fetch data ---
data, skipped_dirs = get_seeding_status(DOWNLOADS_PATH)
df = pd.DataFrame(data)

if not df.empty:
    # Sort by time remaining ascending — closest to safe appears first
    df = df.sort_values("_remaining_sec", ascending=True).reset_index(drop=True)

    # Search
    search_query = st.text_input("🔍 Search files (e.g. 'Night Manager' or '.mkv')", "")
    if search_query:
        df = df[df["File"].str.contains(search_query, case=False, na=False)]

    # Row highlighting
    def highlight_status(row):
        if row["Status"] == "✅ Safe to Delete":
            return ["background-color: rgba(0, 255, 0, 0.1)"] * len(row)
        return [""] * len(row)

    # Display — hide internal columns
    st.dataframe(
        df.style.apply(highlight_status, axis=1),
        width="stretch",
        hide_index=True,
        column_config={
            "IsSafe": None,
            "_remaining_sec": None,
        },
    )

    # Summary
    safe_count = len(df[df["Status"] == "✅ Safe to Delete"])
    st.info(f"Summary: {len(df)} files tracked. **{safe_count}** ready for cleanup.")

    # Feedback on skipped directories
    if skipped_dirs > 0:
        st.caption(f"ℹ️ {skipped_dirs} subdirector{'y' if skipped_dirs == 1 else 'ies'} skipped (files only).")

else:
    if not os.path.exists(DOWNLOADS_PATH):
        st.error(f"Path not found: `{DOWNLOADS_PATH}`")
    else:
        st.warning("No files found in the downloads folder.")

# --- Trigger rerun after 60s if auto-refresh is on ---
if auto_refresh:
    time.sleep(60)
    st.rerun()
