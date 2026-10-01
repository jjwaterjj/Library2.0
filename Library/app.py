from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

DATABASE = "library.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """Convert sqlite3.Row to dict so templates can use book.id and book['id']."""
    if row is None:
        return None
    return dict(row)


def create_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS books(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            year INTEGER,
            genre TEXT
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    current_genre = request.args.get("genre", "").strip()

    conn = get_db()

    genres = [
        row["genre"]
        for row in conn.execute(
            """
            SELECT DISTINCT genre
            FROM books
            WHERE genre IS NOT NULL AND genre != ''
            ORDER BY genre
            """
        ).fetchall()
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

    books = [row_to_dict(row) for row in conn.execute(query, params).fetchall()]
    conn.close()

    return render_template(
        "index.html",
        books=books,
        search=search,
        genres=genres,
        current_genre=current_genre,
    )


@app.route("/add", methods=["GET", "POST"])
def add():

    if request.method == "POST":

        title = request.form["title"]
        author = request.form["author"]
        year = request.form["year"]
        genre = request.form["genre"]

        conn = get_db()

        conn.execute("""
            INSERT INTO books
            (title, author, year, genre)
            VALUES (?, ?, ?, ?)
        """, (
            title,
            author,
            year,
            genre
        ))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    conn = get_db()

    if request.method == "POST":

        title = request.form["title"]
        author = request.form["author"]
        year = request.form["year"]
        genre = request.form["genre"]

        conn.execute("""
            UPDATE books
            SET title=?,
                author=?,
                year=?,
                genre=?
            WHERE id=?
        """, (
            title,
            author,
            year,
            genre,
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/")

    book = row_to_dict(
        conn.execute(
            "SELECT * FROM books WHERE id=?",
            (id,)
        ).fetchone()
    )

    conn.close()

    if not book:
        return "Book Not Found", 404

    return render_template(
        "edit.html",
        book=book
    )


@app.route("/books/<int:id>", methods=["PUT"])
def put_books(id):

    data = request.get_json()

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id=?",
        (id,)
    ).fetchone()

    if not book:
        conn.close()
        return {"message": "Book Not Found"}, 404

    conn.execute("""
        UPDATE books
        SET title=?,
            author=?,
            year=?,
            genre=?
        WHERE id=?
    """, (
        data["title"],
        data["author"],
        data["year"],
        data["genre"],
        id
    ))

    conn.commit()
    conn.close()

    return {"message": "Book Updated Successfully"}, 200


@app.route("/books/<int:id>", methods=["PATCH"])
def patch_books(id):

    data = request.get_json()

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id=?",
        (id,)
    ).fetchone()

    if not book:
        conn.close()
        return {"message": "Book Not Found"}, 404

    title = data.get("title", book["title"])
    author = data.get("author", book["author"])
    year = data.get("year", book["year"])
    genre = data.get("genre", book["genre"])

    conn.execute("""
        UPDATE books
        SET title=?,
            author=?,
            year=?,
            genre=?
        WHERE id=?
    """, (
        title,
        author,
        year,
        genre,
        id
    ))

    conn.commit()
    conn.close()

    return {"message": "Book Updated Successfully"}, 200


@app.route("/delete/<int:id>")
def delete(id):

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id=?",
        (id,)
    ).fetchone()

    if not book:
        conn.close()
        return "Book Not Found", 404

    conn.execute(
        "DELETE FROM books WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/books/<int:id>")
def book(id):

    conn = get_db()

    book = row_to_dict(
        conn.execute(
            "SELECT * FROM books WHERE id=?",
            (id,)
        ).fetchone()
    )

    conn.close()

    if not book:
        return "Book Not Found", 404

    return render_template(
        "book.html",
        book=book
    )


if __name__ == "__main__":

    create_table()

    app.run(debug=True)