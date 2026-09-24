from flask import (
    Blueprint, render_template, request,
    redirect, session, url_for, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3

authorization = Blueprint("auth", __name__)

DATABASE = "library.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "21436587"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_users_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)

    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(users)").fetchall()
    ]

    if "role" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'"
        )

    admin = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (ADMIN_USERNAME,)
    ).fetchone()

    if not admin:
        conn.execute("""
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        """, (
            ADMIN_USERNAME,
            generate_password_hash(ADMIN_PASSWORD),
            "admin"
        ))
    else:

        conn.execute(
            "UPDATE users SET role = 'admin' WHERE username = ?",
            (ADMIN_USERNAME,)
        )

    conn.commit()
    conn.close()



def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))

        if session.get("role") != "admin":
            abort(403)

        return f(*args, **kwargs)

    return decorated


@authorization.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("index"))

    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            error = "Please fill in all fields."

        elif len(username) < 3:
            error = "Username must be at least 3 characters."

        elif username.lower() == ADMIN_USERNAME:
            error = "This username is reserved."

        elif len(password) < 6:
            error = "Password must be at least 6 characters."

        elif password != confirm_password:
            error = "Passwords do not match."

        else:
            conn = get_db()

            existing_user = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if existing_user:
                error = "This username is already taken."
            else:
                conn.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES (?, ?, ?)
                """, (
                    username,
                    generate_password_hash(password),
                    "user"
                ))

                conn.commit()

                user = conn.execute(
                    "SELECT id, username, role FROM users WHERE username = ?",
                    (username,)
                ).fetchone()

                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]

                conn.close()
                return redirect(url_for("index"))

            conn.close()

    return render_template(
        "authorization.html",
        mode="signup",
        error=error
    )


@authorization.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("index"))

        error = "Invalid username or password."

    return render_template(
        "authorization.html",
        mode="login",
        error=error
    )


@authorization.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))