"""ACEest Fitness & Gym - Flask web application.

Web version of the legacy Tkinter desktop app (aceest_fitness.py).
Keeps the same core logic: clients, programs, calorie estimates, BMI,
membership status, weekly adherence and workout logging, stored in SQLite.
"""

import os
import random
import sqlite3
from datetime import date

from flask import (Flask, abort, flash, g, jsonify, redirect,
                   render_template, request, url_for)

# ---------- DOMAIN DATA ----------
PROGRAMS = {
    "Fat Loss": {
        "workout": "Mon: 5x5 Back Squat + AMRAP\nTue: EMOM 20min Assault Bike\n"
                   "Wed: Bench Press + 21-15-9\nThu: 10RFT Deadlifts/Box Jumps\n"
                   "Fri: 30min Active Recovery",
        "diet": "B: 3 Egg Whites + Oats Idli\nL: Grilled Chicken + Brown Rice\n"
                "D: Fish Curry + Millet Roti\nTarget: 2,000 kcal",
        "calorie_factor": 22,
    },
    "Muscle Gain": {
        "workout": "Mon: Squat 5x5\nTue: Bench 5x5\nWed: Deadlift 4x6\n"
                   "Thu: Front Squat 4x8\nFri: Incline Press 4x10\nSat: Barbell Rows 4x10",
        "diet": "B: 4 Eggs + PB Oats\nL: Chicken Biryani (250g Chicken)\n"
                "D: Mutton Curry + Jeera Rice\nTarget: 3,200 kcal",
        "calorie_factor": 35,
    },
    "Beginner": {
        "workout": "Circuit Training: Air Squats, Ring Rows, Push-ups.\n"
                   "Focus: Technique Mastery & Form (90% Threshold)",
        "diet": "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati.\nProtein: 120g/day",
        "calorie_factor": 26,
    },
}

PROGRAM_TEMPLATES = {
    "Fat Loss": ["Full Body HIIT", "Circuit Training", "Cardio + Weights"],
    "Muscle Gain": ["Push/Pull/Legs", "Upper/Lower Split", "Full Body Strength"],
    "Beginner": ["Full Body 3x/week", "Light Strength + Mobility"],
}


# ---------- CORE LOGIC (pure functions, easy to unit test) ----------
def calculate_calories(weight_kg, program):
    """Daily calorie estimate = body weight (kg) x program calorie factor."""
    if program not in PROGRAMS:
        raise ValueError(f"Unknown program: {program}")
    if weight_kg is None or weight_kg <= 0:
        raise ValueError("Weight must be greater than 0")
    return int(weight_kg * PROGRAMS[program]["calorie_factor"])


def calculate_bmi(height_cm, weight_kg):
    """Return (bmi, category) or raise ValueError for invalid input."""
    if not height_cm or not weight_kg or height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be greater than 0")
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1)
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    return bmi, category


def membership_status(membership_end, today=None):
    """'Active' until the end date (inclusive), then 'Expired'; 'N/A' if unset."""
    if not membership_end:
        return "N/A"
    today = today or date.today()
    end = date.fromisoformat(membership_end)
    return "Active" if end >= today else "Expired"


def generate_program(program_type=None, rng=random):
    """Pick a program template, optionally within a given program type."""
    if program_type is None:
        program_type = rng.choice(list(PROGRAM_TEMPLATES))
    if program_type not in PROGRAM_TEMPLATES:
        raise ValueError(f"Unknown program: {program_type}")
    return program_type, rng.choice(PROGRAM_TEMPLATES[program_type])


# ---------- DATABASE ----------
SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    age INTEGER,
    height REAL,
    weight REAL,
    program TEXT,
    calories INTEGER,
    generated_plan TEXT,
    membership_end TEXT
);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    week TEXT NOT NULL,
    adherence INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT NOT NULL,
    workout_type TEXT NOT NULL,
    duration_min INTEGER,
    notes TEXT
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(g.app_db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db(path):
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)


def _to_float(value):
    return float(value) if value not in (None, "") else None


def _to_int(value):
    return int(value) if value not in (None, "") else None


def create_client(db, data):
    """Validate and insert a client. Returns the stored row as a dict."""
    name = (data.get("name") or "").strip()
    program = data.get("program")
    if not name:
        raise ValueError("Name is required")
    if program not in PROGRAMS:
        raise ValueError("Select a valid program")
    try:
        age = _to_int(data.get("age"))
        height = _to_float(data.get("height"))
        weight = _to_float(data.get("weight"))
    except (TypeError, ValueError):
        raise ValueError("Age, height and weight must be numbers")
    membership_end = data.get("membership_end") or None
    if membership_end:
        date.fromisoformat(membership_end)  # raises ValueError if invalid
    calories = calculate_calories(weight, program) if weight else None
    try:
        db.execute(
            "INSERT INTO clients (name, age, height, weight, program, calories, membership_end)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, age, height, weight, program, calories, membership_end),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"Client '{name}' already exists")
    return get_client(db, name)


def get_client(db, name):
    row = db.execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    if row is None:
        return None
    client = dict(row)
    client["membership_status"] = membership_status(client["membership_end"])
    try:
        client["bmi"], client["bmi_category"] = calculate_bmi(client["height"], client["weight"])
    except ValueError:
        client["bmi"], client["bmi_category"] = None, None
    return client


# ---------- APP FACTORY ----------
def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.environ.get("ACEEST_DB", "aceest.db"),
    )
    if test_config:
        app.config.update(test_config)

    init_db(app.config["DATABASE"])

    @app.before_request
    def _set_db_path():
        g.app_db_path = app.config["DATABASE"]

    @app.teardown_appcontext
    def _close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def _client_or_404(name):
        client = get_client(get_db(), name)
        if client is None:
            abort(404)
        return client

    # ----- HTML pages -----
    @app.route("/")
    def index():
        clients = get_db().execute("SELECT name, program FROM clients ORDER BY name").fetchall()
        return render_template("index.html", clients=clients, programs=PROGRAMS)

    @app.route("/clients", methods=["POST"])
    def add_client():
        try:
            client = create_client(get_db(), request.form)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))
        flash(f"Client '{client['name']}' saved", "ok")
        return redirect(url_for("client_detail", name=client["name"]))

    @app.route("/clients/<name>")
    def client_detail(name):
        client = _client_or_404(name)
        db = get_db()
        progress = db.execute(
            "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id", (name,)
        ).fetchall()
        workouts = db.execute(
            "SELECT date, workout_type, duration_min, notes FROM workouts"
            " WHERE client_name = ? ORDER BY date DESC", (name,)
        ).fetchall()
        return render_template("client.html", client=client, program=PROGRAMS.get(client["program"]),
                               progress=progress, workouts=workouts)

    @app.route("/clients/<name>/generate", methods=["POST"])
    def generate(name):
        client = _client_or_404(name)
        _, plan = generate_program(client["program"])
        db = get_db()
        db.execute("UPDATE clients SET generated_plan = ? WHERE name = ?", (plan, name))
        db.commit()
        flash(f"Generated plan: {plan}", "ok")
        return redirect(url_for("client_detail", name=name))

    @app.route("/clients/<name>/progress", methods=["POST"])
    def add_progress(name):
        _client_or_404(name)
        try:
            adherence = int(request.form.get("adherence", ""))
            if not 0 <= adherence <= 100:
                raise ValueError
        except ValueError:
            flash("Adherence must be a number from 0 to 100", "error")
            return redirect(url_for("client_detail", name=name))
        week = request.form.get("week") or date.today().strftime("Week %U - %Y")
        db = get_db()
        db.execute("INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
                   (name, week, adherence))
        db.commit()
        flash("Progress saved", "ok")
        return redirect(url_for("client_detail", name=name))

    @app.route("/clients/<name>/workouts", methods=["POST"])
    def add_workout(name):
        _client_or_404(name)
        workout_type = (request.form.get("workout_type") or "").strip()
        workout_date = request.form.get("date") or date.today().isoformat()
        try:
            date.fromisoformat(workout_date)
            duration = _to_int(request.form.get("duration_min"))
            if not workout_type:
                raise ValueError
        except ValueError:
            flash("Enter a workout type, a valid date and a numeric duration", "error")
            return redirect(url_for("client_detail", name=name))
        db = get_db()
        db.execute(
            "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)"
            " VALUES (?, ?, ?, ?, ?)",
            (name, workout_date, workout_type, duration, request.form.get("notes", "")),
        )
        db.commit()
        flash("Workout logged", "ok")
        return redirect(url_for("client_detail", name=name))

    # ----- JSON API -----
    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.route("/api/programs")
    def api_programs():
        return jsonify(PROGRAMS)

    @app.route("/api/clients", methods=["GET", "POST"])
    def api_clients():
        db = get_db()
        if request.method == "POST":
            try:
                client = create_client(db, request.get_json(silent=True) or {})
            except ValueError as exc:
                return jsonify(error=str(exc)), 400
            return jsonify(client), 201
        rows = db.execute("SELECT name FROM clients ORDER BY name").fetchall()
        return jsonify([get_client(db, r["name"]) for r in rows])

    @app.route("/api/clients/<name>")
    def api_client(name):
        return jsonify(_client_or_404(name))

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
