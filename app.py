import streamlit as st
import sqlite3
import random
import string
from datetime import datetime
import hashlib
import pandas as pd

st.set_page_config(page_title="Link Management Platform", layout="wide")

# ---------- DB ----------
conn = sqlite3.connect("links.db", check_same_thread=False)
c = conn.cursor()

# Users table
c.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

# Links table (full schema)
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

# --- Auto-migrate if older DB missing columns ---
def ensure_column(table, column_def):
    col = column_def.split()[0]
    c.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in c.fetchall()]
    if col not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
        conn.commit()

ensure_column("links", "clicks INTEGER DEFAULT 0")
ensure_column("links", "click_limit INTEGER DEFAULT 0")
ensure_column("links", "active INTEGER DEFAULT 1")
ensure_column("links", "created_at TEXT")
ensure_column("links", "last_accessed TEXT")
ensure_column("links", "user TEXT")

# ---------- UTILS ----------
def generate_short():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ---------- SESSION ----------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------- REDIRECT ----------
params = st.query_params
if "code" in params:
    code = params["code"]
    c.execute("SELECT original, clicks, click_limit, active FROM links WHERE short=?", (code,))
    row = c.fetchone()
    if row:
        original, clicks, limit, active = row

        if active == 0:
            st.error("❌ This link is disabled.")
            st.stop()

        if limit and clicks >= limit:
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

# ---------- AUTH ----------
menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

if st.session_state.user is None:
    if menu == "Register":
        st.title("📝 Register")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Create Account"):
            if not u or not p:
                st.error("Enter username and password")
            else:
                try:
                    c.execute("INSERT INTO users(username,password) VALUES (?,?)", (u, hash_password(p)))
                    conn.commit()
                    st.success("Account created! Go to Login.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists.")

    if menu == "Login":
        st.title("🔐 Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, hash_password(p)))
            user = c.fetchone()
            if user:
                st.session_state.user = u
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

    st.stop()

# ---------- LOGOUT ----------
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ---------- DASHBOARD ----------
st.title("🔗 Link Management Platform")

url = st.text_input("Destination URL")
click_limit = st.number_input("Click Limit (0 = unlimited)", min_value=0, step=1)

if st.button("Create Short Link"):
    if not url.strip():
        st.error("Enter a valid URL")
    else:
        if not url.startswith("http"):
            url = "https://" + url
        short = generate_short()
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO links(short, original, clicks, click_limit, active, created_at, last_accessed, user) VALUES (?,?,?,?,?,?,?,?)",
            (short, url, 0, click_limit, 1, created, None, st.session_state.user)
        )
        conn.commit()
        st.success("Short link created!")
        st.markdown(f"[Open Short Link](?code={short})")

# ---------- USER LINKS ----------
st.subheader("📊 Your Links")

c.execute("SELECT * FROM links WHERE user=?", (st.session_state.user,))
rows = c.fetchall()

if rows:
    df = pd.DataFrame(rows, columns=[
        "Short", "URL", "Clicks", "Limit", "Active", "Created", "Last Access", "User"
    ])
    st.dataframe(df, use_container_width=True)

    st.write("### Manage Links")
    for short, original, clicks, limit, active, created, last_access, user in rows:
        st.write("---")
        st.markdown(f"**Short:** `{short}`  |  [Open](?code={short})")

        # Edit URL
        new_url = st.text_input("Edit Destination URL", value=original, key=f"url_{short}")
        if st.button("Update URL", key=f"update_{short}"):
            if not new_url.startswith("http"):
                new_url = "https://" + new_url
            c.execute("UPDATE links SET original=? WHERE short=?", (new_url, short))
            conn.commit()
            st.success("URL updated")

        # Enable / Disable toggle
        toggle = st.toggle("Enable / Disable Link", value=bool(active), key=f"toggle_{short}")
        if toggle != bool(active):
            c.execute("UPDATE links SET active=? WHERE short=?", (int(toggle), short))
            conn.commit()

        st.write(f"Clicks: **{clicks}**")
        st.write(f"Limit: **{limit}**")
        st.write(f"Created: **{created}**")
        st.write(f"Last Accessed: **{last_access}**")
else:
    st.info("No links created yet.")
