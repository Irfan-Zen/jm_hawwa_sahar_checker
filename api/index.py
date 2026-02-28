from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "sahar_secret_key"
 
def init_db():
    conn = sqlite3.connect("/tmp/tokens.db")
    c = conn.cursor()
 
    c.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token_number INTEGER UNIQUE
        )
    """)
 
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            approved INTEGER DEFAULT 0
        )
    """)
 
    c.execute("SELECT * FROM users WHERE role='admin'")
    if not c.fetchone():
        c.execute("""
            INSERT INTO users (username, password, role, approved)
            VALUES (?, ?, ?, ?)
        """, ("admin", "admin123", "admin", 1))

    conn.commit()
    conn.close()


init_db()
 
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect("/tmp/tokens.db")
        c = conn.cursor()
        c.execute("""
            SELECT id, role, approved FROM users
            WHERE username=? AND password=?
        """, (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            if user[2] == 0:
                error = "⏳ Waiting for admin approval."
            else:
                session["user_id"] = user[0]
                session["role"] = user[1]
                return redirect("/")
        else:
            error = "❌ Invalid credentials."

    return render_template("login.html", error=error)
 
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect("/tmp/tokens.db")
        c = conn.cursor()

        try:
            c.execute("""
                INSERT INTO users (username, password, role)
                VALUES (?, ?, ?)
            """, (username, password, "servant"))
            conn.commit()
            message = "✅ Registered successfully! Wait for admin approval."
        except:
            message = "❌ Username already exists."

        conn.close()

    return render_template("register.html", message=message)
 
@app.route("/", methods=["GET", "POST"])
def home():

    if not session.get("user_id"):
        return redirect("/login")

    message = ""
    total = 0
    show_list = False
    tokens = []

    conn = sqlite3.connect("/tmp/tokens.db")
    c = conn.cursor()

    if request.method == "POST":

        if "add" in request.form:
            token = request.form.get("token")

            if token:
                try:
                    c.execute("INSERT INTO tokens (token_number) VALUES (?)", (token,))
                    conn.commit()
                    message = "✅ Token added successfully!"
                except sqlite3.IntegrityError:
                    message = "❌ Token already exists!"

        elif "show" in request.form:
            show_list = True

    c.execute("SELECT COUNT(*) FROM tokens")
    total = c.fetchone()[0]

    if show_list:
        c.execute("SELECT token_number FROM tokens ORDER BY token_number ASC")
        tokens = [row[0] for row in c.fetchall()]
 
    pending_users = []
    if session.get("role") == "admin":
        c.execute("SELECT id, username FROM users WHERE role='servant' AND approved=0")
        pending_users = c.fetchall()

    conn.close()

    return render_template("index.html",
                           message=message,
                           total=total,
                           show_list=show_list,
                           tokens=tokens,
                           role=session.get("role"),
                           pending_users=pending_users)
 
@app.route("/approve/<int:user_id>")
def approve(user_id):

    if session.get("role") != "admin":
        return redirect("/")

    conn = sqlite3.connect("/tmp/tokens.db")
    c = conn.cursor()
    c.execute("UPDATE users SET approved=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/")
 
@app.route("/reset", methods=["POST"])
def reset():

    if session.get("role") != "admin":
        return redirect("/")

    conn = sqlite3.connect("/tmp/tokens.db")
    c = conn.cursor()
    c.execute("DELETE FROM tokens")
    conn.commit()
    conn.close()

    return redirect("/") 

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

handler = app