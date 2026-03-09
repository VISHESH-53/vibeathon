import streamlit as st
import sqlite3
import random
import string

# ---------- Database ----------
conn = sqlite3.connect("urls.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS links(
short TEXT PRIMARY KEY,
original TEXT,
clicks INTEGER
)
""")
conn.commit()


# ---------- Generate Short Code ----------
def generate_short():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


# ---------- Redirect Logic ----------
params = st.query_params

if "code" in params:

    code = params["code"]

    c.execute("SELECT original FROM links WHERE short=?", (code,))
    row = c.fetchone()

    if row:
        original = row[0]

        # increase click count
        c.execute(
            "UPDATE links SET clicks = clicks + 1 WHERE short=?",
            (code,)
        )
        conn.commit()

        # redirect automatically
        st.markdown(
            f'<meta http-equiv="refresh" content="0;url={original}">',
            unsafe_allow_html=True
        )

        st.stop()


# ---------- UI ----------
st.title("🔗 Link Analytics Shortener")

url = st.text_input("Enter Long URL")

if st.button("Shorten URL"):

    if url.strip() == "":
        st.error("URL cannot be empty")

    else:

        # auto add https if missing
        if not url.startswith("http"):
            url = "https://" + url

        short = generate_short()

        c.execute(
            "INSERT INTO links VALUES (?, ?, ?)",
            (short, url, 0)
        )
        conn.commit()

        short_link = f"?code={short}"

        st.success("Short URL Created!")

        st.markdown(f"### Short Link")
        st.markdown(f"[Open Short URL]({short_link})")


# ---------- Dashboard ----------
st.subheader("📊 Link Dashboard")

c.execute("SELECT * FROM links")
data = c.fetchall()

for short, original, clicks in data:

    st.write("Original URL:", original)
    st.markdown(f"Short URL: [?code={short}](?code={short})")
    st.write("Total Clicks:", clicks)
    st.write("---")
