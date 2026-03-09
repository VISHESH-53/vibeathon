import streamlit as st
import sqlite3
import random
import string
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Link Management Platform", layout="wide")

# ---------- DATABASE ----------
conn = sqlite3.connect("links.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS links(
short TEXT PRIMARY KEY,
original TEXT,
clicks INTEGER,
click_limit INTEGER,
active INTEGER,
created_at TEXT,
last_accessed TEXT
)
""")
conn.commit()


# ---------- SHORT CODE ----------
def generate_short():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


# ---------- REDIRECT LOGIC ----------
params = st.query_params

if "code" in params:

    code = params["code"]

    c.execute("SELECT original, clicks, click_limit, active FROM links WHERE short=?", (code,))
    row = c.fetchone()

    if row:

        original, clicks, limit, active = row

        if not active:
            st.error("❌ This link is disabled.")
            st.stop()

        if limit != 0 and clicks >= limit:
            st.error("⛔ This link has expired (click limit reached).")
            st.stop()

        c.execute(
            "UPDATE links SET clicks = clicks + 1, last_accessed=? WHERE short=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), code)
        )
        conn.commit()

        st.markdown(
            f'<meta http-equiv="refresh" content="0;url={original}">',
            unsafe_allow_html=True
        )

        st.stop()


# ---------- UI ----------
st.title("🔗 Link Management Platform")

st.write("Create and manage shortened links with analytics and controls.")

# ---------- CREATE LINK ----------
url = st.text_input("Enter Destination URL")

click_limit = st.number_input(
    "Optional Click Limit (0 = unlimited)",
    min_value=0,
    step=1
)

if st.button("Create Short Link"):

    if url.strip() == "":
        st.error("Please enter a valid URL")

    else:

        if not url.startswith("http"):
            url = "https://" + url

        short = generate_short()

        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute(
            "INSERT INTO links VALUES (?,?,?,?,?,?,?)",
            (short, url, 0, click_limit, 1, created, None)
        )

        conn.commit()

        short_link = f"?code={short}"

        st.success("Short link created")

        st.markdown(f"[Open Short URL]({short_link})")


# ---------- DASHBOARD ----------
st.subheader("📊 Link Dashboard")

c.execute("SELECT * FROM links")
rows = c.fetchall()

if rows:

    df = pd.DataFrame(rows, columns=[
        "Short",
        "Original URL",
        "Clicks",
        "Click Limit",
        "Active",
        "Created At",
        "Last Accessed"
    ])

    st.dataframe(df)

    st.write("### Manage Links")

    for short, original, clicks, limit, active, created, last_access in rows:

        st.write("---")
        st.write("Short:", short)

        st.markdown(f"Short URL: [?code={short}](?code={short})")

        # EDIT URL
        new_url = st.text_input(
            f"Edit URL {short}",
            value=original,
            key=f"url_{short}"
        )

        if st.button("Update URL", key=f"update_{short}"):

            c.execute(
                "UPDATE links SET original=? WHERE short=?",
                (new_url, short)
            )

            conn.commit()

            st.success("URL updated")

        # ENABLE / DISABLE
        status = st.checkbox(
            "Active",
            value=bool(active),
            key=f"active_{short}"
        )

        c.execute(
            "UPDATE links SET active=? WHERE short=?",
            (int(status), short)
        )

        conn.commit()

        st.write("Clicks:", clicks)
        st.write("Limit:", limit)
        st.write("Created:", created)
        st.write("Last Accessed:", last_access)

else:
    st.info("No links created yet.")
