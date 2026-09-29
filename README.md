# 📚 Library Management System

## About the Project

The Library Management System is a web application built with Python and Flask. It allows users to browse books, search for books, and view detailed information. An administrator can manage the library's book collection.

## Features

### Public Users

* View all books in the library.
* Search for books by title or author.
* Filter books by genre.
* View detailed information about each book.
* Create an account and log in.

### Administrator

* Log in using the administrator account.
* Add new books to the library.
* Edit existing book information.
* Delete books from the library.
* Upload book cover images.
* Manage book descriptions and other details.

### Security

* User registration and login system.
* Passwords are stored as hashes.
* Only the administrator can add, edit, or delete books.
* Regular users can browse the library but cannot manage books.

## Technologies Used

* **Python** — Main programming language.
* **Flask** — Web application framework.
* **SQLite** — Database for storing books and user accounts.
* **HTML** — Page structure.
* **CSS** — Website styling.
* **Jinja2** — Dynamic HTML templates.

## Project Structure

```text
Library/
│
├── app.py
├── authorization.py
├── library.db
│
├── templates/
│   ├── authorization.html
│   ├── index.html
│   ├── book.html
│   ├── add.html
│   └── edit.html
│
└── static/
    ├── styles.css
    └── images/
```

## Installation and Setup

### 1. Install Python

Make sure Python is installed on your computer.

### 2. Install Flask

Open the terminal in your project folder and run:

```bash
pip install flask
```

### 3. Run the Application

Run the following command:

```bash
python app.py
```

### 4. Open the Website

Open your browser and visit:

http://127.0.0.1:5000/

## Database

The application uses SQLite to store:

* Book titles, authors, publication years, genres, images, and descriptions.
* User accounts and roles.

## Purpose

The purpose of this project is to create a simple and accessible online library where users can discover books and an administrator can manage the collection.
