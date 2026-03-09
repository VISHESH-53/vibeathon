import streamlit as st
import sqlite3
import random
import string
from datetime import datetime
import hashlib
import pandas as pd

st.set_page_config(page_title="Link Management Platform", layout="wide")

# ---------- DATABASE ----------
conn = sqlite3.connect("links.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE,
password TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS links(
short TEXT PRIMARY KEY,
original TEXT,
clicks INTEGER,
click_limit INTEGER,
active INTEGER,
created_at TEXT,
last_accessed TEXT,
user TEXT
)
""")

conn.commit()


# ---------- UTILS ----------
def generate_short():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ---------- SESSION ----------
if "user" not in st.session_state:
    st.session_state.user = None


# ---------- REDIRECT ----------
params = st.query_params

if "code" in params:

    code = params["code"]

    c.execute(
        "SELECT original, clicks, click_limit, active FROM links WHERE short=?",
        (code,)
    )

    row = c.fetchone()

    if row:

        original, clicks, limit, active = row

        if active == 0:
            st.error("❌ This link is disabled.")
            st.stop()

        if limit != 0 and clicks >= limit:
            st.error("⛔ This link has expired.")
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


# ---------- LOGIN / REGISTER ----------
menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

if st.session_state.user is None:

    if menu == "Register":

        st.title("📝 Register")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Create Account"):

            try:
                c.execute(
                    "INSERT INTO users(username,password) VALUES (?,?)",
                    (username, hash_password(password))
                )

                conn.commit()

                st.success("Account created successfully!")

            except:
                st.error("Username already exists")

    if menu == "Login":

        st.title("🔐 Login")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):

            c.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, hash_password(password))
            )

            user = c.fetchone()

            if user:
                st.session_state.user = username
                st.success("Login successful")
                st.rerun()

            else:
                st.error("Invalid credentials")

    st.stop()


# ---------- LOGOUT ----------
st.sidebar.write(f"Logged in as: {st.session_state.user}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()


# ---------- DASHBOARD ----------
st.title("🔗 Link Management Platform")

st.write("Create and manage shortened links.")


# ---------- CREATE LINK ----------
url = st.text_input("Destination URL")

click_limit = st.number_input(
    "Click Limit (0 = unlimited)",
    min_value=0,
    step=1
)

if st.button("Create Short Link"):

    if url.strip() == "":
        st.error("Enter a valid URL")

    else:

        if not url.startswith("http"):
            url = "https://" + url

        short = generate_short()

        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute(
            "INSERT INTO links VALUES (?,?,?,?,?,?,?,?)",
            (short, url, 0, click_limit, 1, created, None, st.session_state.user)
        )

        conn.commit()

        st.success("Short link created!")

        st.markdown(f"[Open Short Link](?code={short})")


# ---------- DASHBOARD TABLE ----------
st.subheader("📊 Your Links")

c.execute(
    "SELECT * FROM links WHERE user=?",
    (st.session_state.user,)
)

rows = c.fetchall()

if rows:

    df = pd.DataFrame(rows, columns=[
        "Short",
        "URL",
        "Clicks",
        "Limit",
        "Active",
        "Created",
        "Last Access",
        "User"
    ])

    st.dataframe(df)

    st.write("### Manage Links")

    for short, original, clicks, limit, active, created, last_access, user in rows:

        st.write("---")

        st.markdown(f"### 🔗 {short}")
        st.markdown(f"[Open Short URL](?code={short})")

        # ---------- EDIT URL ----------
        new_url = st.text_input(
            "Edit Destination URL",
            value=original,
            key=f"url_{short}"
        )

        if st.button("Update URL", key=f"update_{short}"):

            if not new_url.startswith("http"):
                new_url = "https://" + new_url

            c.execute(
                "UPDATE links SET original=? WHERE short=?",
                (new_url, short)
            )

            conn.commit()

            st.success("URL updated")

        # ---------- ENABLE / DISABLE ----------
        toggle_status = st.toggle(
            "Enable / Disable Link",
            value=bool(active),
            key=f"toggle_{short}"
        )

        if toggle_status != bool(active):

            c.execute(
                "UPDATE links SET active=? WHERE short=?",
                (int(toggle_status), short)
            )

            conn.commit()

        st.write("Clicks:", clicks)
        st.write("Limit:", limit)
        st.write("Created:", created)
        st.write("Last Accessed:", last_access)

else:
    st.info("No links created yet.")
