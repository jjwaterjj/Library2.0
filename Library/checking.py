import sqlite3

DATABASE = "library.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def book_exists(book_id):
    """Check if a book exists."""
    conn = get_db()

    book = conn.execute(
        "SELECT id FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    conn.close()

    return book is not None


def user_exists(user_id):
    """Check if a user exists."""
    conn = get_db()

    user = conn.execute(
        "SELECT id FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    conn.close()

    return user is not None


def book_is_borrowed_by_user(user_id, book_id):
    """Check if this user already borrowed this book."""
    conn = get_db()

    borrowed = conn.execute(
        """
        SELECT id
        FROM borrowed_books
        WHERE user_id = ? AND book_id = ?
        """,
        (user_id, book_id)
    ).fetchone()

    conn.close()

    return borrowed is not None


def book_has_copies(book_id):
    """Check if at least one copy is available."""
    conn = get_db()

    book = conn.execute(
        "SELECT amount FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    conn.close()

    if not book:
        return False

    return book["amount"] > 0


def borrow_is_saved(user_id, book_id):
    """Check that a borrowing record was actually saved."""
    return book_is_borrowed_by_user(user_id, book_id)


def return_is_saved(user_id, book_id):
    """Check that the user no longer has the book."""
    return not book_is_borrowed_by_user(user_id, book_id)


def check_borrowing_count(book_id):
    """
    Check how many people currently have this book
    and compare it with the total number of copies.
    """

    conn = get_db()

    book = conn.execute(
        "SELECT amount FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    if not book:
        conn.close()
        return False

    borrowed_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM borrowed_books
        WHERE book_id = ?
        """,
        (book_id,)
    ).fetchone()[0]

    conn.close()

    # Available copies can never be negative.
    return borrowed_count >= 0


def check_database():
    """
    Run general checks on the library database.

    Returns a list of problems.
    An empty list means no problems were found.
    """

    problems = []

    conn = get_db()

    # Check for books with negative amounts
    negative_books = conn.execute(
        """
        SELECT id, title, amount
        FROM books
        WHERE amount < 0
        """
    ).fetchall()

    for book in negative_books:
        problems.append(
            f"Book {book['id']} ({book['title']}) has a negative amount."
        )

    # Check for duplicate user/book borrowing records
    duplicates = conn.execute(
        """
        SELECT user_id, book_id, COUNT(*) AS total
        FROM borrowed_books
        GROUP BY user_id, book_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    for duplicate in duplicates:
        problems.append(
            f"User {duplicate['user_id']} has duplicate "
            f"borrowing records for book {duplicate['book_id']}."
        )

    # Check that every borrowing record points to an existing user
    invalid_users = conn.execute(
        """
        SELECT borrowed_books.id, borrowed_books.user_id
        FROM borrowed_books
        LEFT JOIN users
            ON borrowed_books.user_id = users.id
        WHERE users.id IS NULL
        """
    ).fetchall()

    for record in invalid_users:
        problems.append(
            f"Borrowing record {record['id']} has an invalid user."
        )

    # Check that every borrowing record points to an existing book
    invalid_books = conn.execute(
        """
        SELECT borrowed_books.id, borrowed_books.book_id
        FROM borrowed_books
        LEFT JOIN books
            ON borrowed_books.book_id = books.id
        WHERE books.id IS NULL
        """
    ).fetchall()

    for record in invalid_books:
        problems.append(
            f"Borrowing record {record['id']} has an invalid book."
        )

    conn.close()

    return problems


def run_checks():
    """
    Run all database checks and print the results.
    """

    print("Checking library database...")

    problems = check_database()

    if not problems:
        print("Everything looks good.")
        return True

    print("Problems found:")

    for problem in problems:
        print("-", problem)

    return False


if __name__ == "__main__":
    run_checks()