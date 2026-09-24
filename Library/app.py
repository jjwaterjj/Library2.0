
from flask import Flask, render_template, request, redirect, url_for, abort
from authorization import (
    authorization,
    create_users_table,
    get_db,
    login_required,
    admin_required
)
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)

DATABASE = "library.db"

UPLOAD_FOLDER = "static/images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.register_blueprint(authorization)

def create_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            year INTEGER,
            genre TEXT,
            image TEXT,
            description TEXT
        )
    """)

    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(books)").fetchall()
    ]

    if "image" not in columns:
        conn.execute("ALTER TABLE books ADD COLUMN image TEXT")

    if "description" not in columns:
        conn.execute("ALTER TABLE books ADD COLUMN description TEXT")

    conn.commit()
    conn.close()

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    current_genre = request.args.get("genre", "").strip()

    conn = get_db()

    genres = [
        row["genre"]
        for row in conn.execute("""
            SELECT DISTINCT genre
            FROM books
            WHERE genre IS NOT NULL AND genre != ''
            ORDER BY genre
        """).fetchall()
    ]

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if search:
        query += " AND (title LIKE ? OR author LIKE ? OR genre LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])

    if current_genre:
        query += " AND genre = ?"
        params.append(current_genre)

    books = [
        dict(row)
        for row in conn.execute(query, params).fetchall()
    ]

    conn.close()

    return render_template(
        "index.html",
        books=books,
        search=search,
        genres=genres,
        current_genre=current_genre
    )

@app.route("/add", methods=["GET", "POST"])
@admin_required
def add():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        year = request.form.get("year", "").strip()
        genre = request.form.get("genre", "").strip()
        description = request.form.get("description", "").strip()

        image = request.files.get("image")
        image_filename = None

        if image and image.filename:
            if allowed_file(image.filename):
                image_filename = secure_filename(image.filename)
                image.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        image_filename
                    )
                )

        conn = get_db()

        conn.execute("""
            INSERT INTO books
            (title, author, year, genre, image, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            title, author, year, genre,
            image_filename, description
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template("add.html")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit(id):
    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (id,)
    ).fetchone()

    if not book:
        conn.close()
        return "Book Not Found", 404

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        year = request.form.get("year", "").strip()
        genre = request.form.get("genre", "").strip()
        description = request.form.get("description", "").strip()

        image_filename = book["image"]
        image = request.files.get("image")

        if image and image.filename:
            if allowed_file(image.filename):
                image_filename = secure_filename(image.filename)
                image.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        image_filename
                    )
                )

        conn.execute("""
            UPDATE books
            SET title = ?,
                author = ?,
                year = ?,
                genre = ?,
                image = ?,
                description = ?
            WHERE id = ?
        """, (
            title, author, year, genre,
            image_filename, description, id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("book", id=id))

    book = dict(book)
    conn.close()

    return render_template("edit.html", book=book)

@app.route("/delete/<int:id>", methods=["POST"])
@admin_required
def delete(id):
    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (id,)
    ).fetchone()

    if not book:
        conn.close()
        return "Book Not Found", 404

    conn.execute(
        "DELETE FROM books WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("index"))

@app.route("/books/<int:id>")
def book(id):
    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (id,)
    ).fetchone()

    conn.close()

    if not book:
        return "Book Not Found", 404

    return render_template("book.html", book=dict(book))

@app.route("/books/<int:id>", methods=["PUT"])
@admin_required
def put_books(id):
    data = request.get_json(silent=True) or {}

    required = ["title", "author", "year", "genre", "description"]

    if not all(key in data for key in required):
        return {"error": "Missing required fields"}, 400

    conn = get_db()

    book = conn.execute(
        "SELECT id FROM books WHERE id = ?",
        (id,)
    ).fetchone()

    if not book:
        conn.close()
        return {"message": "Book Not Found"}, 404

    conn.execute("""
        UPDATE books
        SET title = ?,
            author = ?,
            year = ?,
            genre = ?,
            description = ?
        WHERE id = ?
    """, (
        data["title"],
        data["author"],
        data["year"],
        data["genre"],
        data["description"],
        id
    ))

    conn.commit()
    conn.close()

    return {"message": "Book Updated Successfully"}, 200

@app.route("/books/<int:id>", methods=["PATCH"])
@admin_required
def patch_books(id):
    data = request.get_json(silent=True) or {}

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (id,)
    ).fetchone()

    if not book:
        conn.close()
        return {"message": "Book Not Found"}, 404

    title = data.get("title", book["title"])
    author = data.get("author", book["author"])
    year = data.get("year", book["year"])
    genre = data.get("genre", book["genre"])
    description = data.get("description", book["description"])

    conn.execute("""
        UPDATE books
        SET title = ?,
            author = ?,
            year = ?,
            genre = ?,
            description = ?
        WHERE id = ?
    """, (
        title, author, year, genre, description, id
    ))

    conn.commit()
    conn.close()

    return {"message": "Book Updated Successfully"}, 200

@app.errorhandler(403)
def forbidden(error):
    return "Access Denied: Admins Only", 403

if __name__ == "__main__":
    create_table()
    create_users_table()
    app.run(debug=True)