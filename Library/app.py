from flask import Flask, render_template, request, redirect, url_for
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
            description TEXT,
            amount INTEGER DEFAULT 1
        )
    """)

    # Check existing columns
    columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(books)"
        ).fetchall()
    ]

    # Add missing columns to an existing database
    if "image" not in columns:
        conn.execute(
            "ALTER TABLE books ADD COLUMN image TEXT"
        )

    if "description" not in columns:
        conn.execute(
            "ALTER TABLE books ADD COLUMN description TEXT"
        )

    if "amount" not in columns:
        conn.execute(
            "ALTER TABLE books ADD COLUMN amount INTEGER DEFAULT 1"
        )

    # Make sure old books have a valid amount
    conn.execute("""
        UPDATE books
        SET amount = 1
        WHERE amount IS NULL OR amount < 0
    """)

    # Table for borrowed books
    conn.execute("""
        CREATE TABLE IF NOT EXISTS borrowed_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            borrowed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, book_id)
        )
    """)

    conn.commit()
    conn.close()


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
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
        query += """
            AND (
                title LIKE ?
                OR author LIKE ?
                OR genre LIKE ?
            )
        """

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

        try:
            amount = int(request.form.get("amount", 1))
            if amount < 0:
                amount = 0
        except ValueError:
            amount = 1

        image = request.files.get("image")
        image_filename = None

        if image and image.filename:
            if allowed_file(image.filename):
                image_filename = secure_filename(
                    image.filename
                )

                image.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        image_filename
                    )
                )

        conn = get_db()

        conn.execute("""
            INSERT INTO books
            (
                title,
                author,
                year,
                genre,
                image,
                description,
                amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            author,
            year,
            genre,
            image_filename,
            description,
            amount
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

        try:
            amount = int(request.form.get("amount", 1))
            if amount < 0:
                amount = 0
        except ValueError:
            amount = 1

        image_filename = book["image"]

        image = request.files.get("image")

        if image and image.filename:
            if allowed_file(image.filename):
                image_filename = secure_filename(
                    image.filename
                )

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
                description = ?,
                amount = ?
            WHERE id = ?
        """, (
            title,
            author,
            year,
            genre,
            image_filename,
            description,
            amount,
            id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("book", id=id))

    book = dict(book)

    conn.close()

    return render_template(
        "edit.html",
        book=book
    )


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

    # Remove borrowing records first
    conn.execute(
        "DELETE FROM borrowed_books WHERE book_id = ?",
        (id,)
    )

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

    borrowed = False

    if "user_id" in request.cookies:
        pass

    # Check whether the logged-in user borrowed this book
    from flask import session

    if session.get("user_id"):
        borrowed_record = conn.execute("""
            SELECT id
            FROM borrowed_books
            WHERE user_id = ? AND book_id = ?
        """, (
            session["user_id"],
            id
        )).fetchone()

        borrowed = borrowed_record is not None

    conn.close()

    if not book:
        return "Book Not Found", 404

    return render_template(
        "book.html",
        book=dict(book),
        borrowed=borrowed
    )


@app.route("/borrow/<int:id>", methods=["POST"])
@login_required
def borrow(id):
    from flask import session

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (id,)
    ).fetchone()

    if not book:
        conn.close()
        return "Book Not Found", 404

    # Check if this user already borrowed the book
    already_borrowed = conn.execute("""
        SELECT id
        FROM borrowed_books
        WHERE user_id = ? AND book_id = ?
    """, (
        session["user_id"],
        id
    )).fetchone()

    if already_borrowed:
        conn.close()
        return redirect(url_for("book", id=id))

    # No copies available
    if book["amount"] <= 0:
        conn.close()
        return redirect(url_for("book", id=id))

    # Decrease available copies
    conn.execute("""
        UPDATE books
        SET amount = amount - 1
        WHERE id = ? AND amount > 0
    """, (id,))

    # Save the borrowing record
    conn.execute("""
        INSERT INTO borrowed_books
        (user_id, book_id)
        VALUES (?, ?)
    """, (
        session["user_id"],
        id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("book", id=id))


@app.route("/return/<int:id>", methods=["POST"])
@login_required
def return_book(id):
    from flask import session

    conn = get_db()

    borrowed = conn.execute("""
        SELECT id
        FROM borrowed_books
        WHERE user_id = ? AND book_id = ?
    """, (
        session["user_id"],
        id
    )).fetchone()

    if borrowed:

        conn.execute("""
            DELETE FROM borrowed_books
            WHERE user_id = ? AND book_id = ?
        """, (
            session["user_id"],
            id
        ))

        conn.execute("""
            UPDATE books
            SET amount = amount + 1
            WHERE id = ?
        """, (id,))

        conn.commit()

    conn.close()

    return redirect(url_for("book", id=id))


@app.route("/books/<int:id>", methods=["PUT"])
@admin_required
def put_books(id):
    data = request.get_json(silent=True) or {}

    required = [
        "title",
        "author",
        "year",
        "genre",
        "description"
    ]

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

    amount = data.get("amount", 1)

    conn.execute("""
        UPDATE books
        SET title = ?,
            author = ?,
            year = ?,
            genre = ?,
            description = ?,
            amount = ?
        WHERE id = ?
    """, (
        data["title"],
        data["author"],
        data["year"],
        data["genre"],
        data["description"],
        amount,
        id
    ))

    conn.commit()
    conn.close()

    return {
        "message": "Book Updated Successfully"
    }, 200


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
    description = data.get(
        "description",
        book["description"]
    )
    amount = data.get("amount", book["amount"])

    conn.execute("""
        UPDATE books
        SET title = ?,
            author = ?,
            year = ?,
            genre = ?,
            description = ?,
            amount = ?
        WHERE id = ?
    """, (
        title,
        author,
        year,
        genre,
        description,
        amount,
        id
    ))

    conn.commit()
    conn.close()

    return {
        "message": "Book Updated Successfully"
    }, 200


@app.errorhandler(403)
def forbidden(error):
    return "Access Denied: Admins Only", 403


if __name__ == "__main__":
    create_table()
    create_users_table()
    app.run(debug=True)
