import os
import sqlite3
from datetime import date
from functools import wraps

try:
    import mysql.connector
except ModuleNotFoundError:
    mysql = None

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, template_folder="template", static_folder="static")

# Secret key for login sessions
app.secret_key = "personal-finance-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "finance.db")

# MySQL configuration (kept for real deployments, but falls back automatically)
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "finance_db"),
    "port": int(os.environ.get("DB_PORT", "3306")),
}


# ---------------- DATABASE CONNECTION ----------------

def get_db():
    if mysql is not None:
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                return connection
        except mysql.connector.Error:
            pass

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def get_cursor(connection, as_dict=False):
    if connection.__class__.__module__.startswith("mysql"):
        return connection.cursor(dictionary=as_dict)
    return connection.cursor()


def init_db():
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    connection.commit()
    cursor.close()
    connection.close()


init_db()


# ---------------- LOGIN REQUIRED ----------------

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# ---------------- HOME ----------------

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"].lower()
        password = request.form["password"]

        if not name or not email or not password:
            flash("Please fill all fields.", "danger")
            return redirect(url_for("register"))

        connection = get_db()
        cursor = get_cursor(connection, as_dict=True)

        cursor.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            connection.close()

            flash("Email already registered.", "warning")

            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (name, email, password_hash)
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash("Registration successful!", "success")

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].lower()
        password = request.form["password"]

        connection = get_db()
        cursor = get_cursor(connection, as_dict=True)

        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_db()
    cursor = get_cursor(connection, as_dict=True)

    cursor.execute(
        """
        SELECT
        COALESCE(
            SUM(CASE WHEN type = 'Income' THEN amount ELSE 0 END), 0
        ) AS income,
        COALESCE(
            SUM(CASE WHEN type = 'Expense' THEN amount ELSE 0 END), 0
        ) AS expense
        FROM transactions
        WHERE user_id = ?
        """,
        (session["user_id"],)
    )

    totals = cursor.fetchone()

    cursor.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE user_id = ? AND type = 'Expense'
        GROUP BY category
        ORDER BY total DESC
        """,
        (session["user_id"],)
    )

    category_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 8
        """,
        (session["user_id"],)
    )

    recent = cursor.fetchall()

    cursor.close()
    connection.close()

    income = float(totals["income"])
    expense = float(totals["expense"])
    balance = income - expense

    return render_template(
        "index.html",
        income=income,
        expense=expense,
        balance=balance,
        category_rows=category_rows,
        recent=recent,
    )


# ---------------- ADD INCOME ----------------

@app.route("/add-income", methods=["GET", "POST"])
@login_required
def add_income():

    if request.method == "POST":

        amount = request.form["amount"]
        category = request.form["category"]
        description = request.form["description"]

        transaction_date = (
            request.form["date"]
            or date.today().isoformat()
        )

        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO transactions
            (
                user_id,
                type,
                category,
                amount,
                description,
                date
            )

            VALUES
            (
                ?,
                'Income',
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                session["user_id"],
                category,
                amount,
                description,
                transaction_date
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash("Income added successfully!", "success")

        return redirect(url_for("dashboard"))

    return render_template("add_income.html")


# ---------------- ADD EXPENSE ----------------

@app.route("/add-expense", methods=["GET", "POST"])
@login_required
def add_expense():

    if request.method == "POST":

        amount = request.form["amount"]
        category = request.form["category"]
        description = request.form["description"]

        transaction_date = (
            request.form["date"]
            or date.today().isoformat()
        )

        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO transactions
            (
                user_id,
                type,
                category,
                amount,
                description,
                date
            )

            VALUES
            (
                ?,
                'Expense',
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                session["user_id"],
                category,
                amount,
                description,
                transaction_date
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash("Expense added successfully!", "success")

        return redirect(url_for("dashboard"))

    return render_template("add_expense.html")


# ---------------- TRANSACTIONS ----------------

@app.route("/transactions")
@login_required
def transactions():

    connection = get_db()
    cursor = get_cursor(connection, as_dict=True)

    cursor.execute(
        """
        SELECT *

        FROM transactions

        WHERE user_id = ?

        ORDER BY date DESC, id DESC
        """,
        (session["user_id"],)
    )

    transaction_list = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "transactions.html",
        transactions=transaction_list
    )


# ---------------- DELETE TRANSACTION ----------------

@app.route(
    "/delete/<int:transaction_id>",
    methods=["POST"]
)
@login_required
def delete_transaction(transaction_id):

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM transactions

        WHERE id = ?

        AND user_id = ?
        """,
        (
            transaction_id,
            session["user_id"]
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    flash(
        "Transaction deleted successfully!",
        "success"
    )

    return redirect(url_for("transactions"))


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":

    app.run(debug=True)