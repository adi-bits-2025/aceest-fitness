"""Integration tests for the Flask routes (HTML pages and JSON API)."""


# ---------- health & API basics ----------
def test_health(anon_client):
    res = anon_client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


def test_api_programs(client):
    data = client.get("/api/programs").get_json()
    assert set(data) == {"Fat Loss", "Muscle Gain", "Beginner"}
    assert data["Muscle Gain"]["calorie_factor"] == 35


# ---------- HTML: clients ----------
def test_index_empty(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"No clients yet" in res.data


def test_add_client_redirects_to_detail(client):
    res = client.post("/clients", data={"name": "Asha", "program": "Beginner"})
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/clients/Asha")


def test_client_detail_shows_computed_values(client, sample_client):
    page = client.get(f"/clients/{sample_client}").get_data(as_text=True)
    assert "1760" in page          # 80 kg x 22
    assert "26.1" in page          # BMI
    assert "Overweight" in page
    assert "Active" in page


def test_index_lists_client(client, sample_client):
    assert b"Ravi" in client.get("/").data


def test_add_client_requires_name(client):
    res = client.post("/clients", data={"name": " ", "program": "Beginner"}, follow_redirects=True)
    assert b"Name is required" in res.data


def test_add_client_rejects_invalid_program(client):
    res = client.post("/clients", data={"name": "X", "program": "Yoga"}, follow_redirects=True)
    assert b"Select a valid program" in res.data


def test_add_duplicate_client(client, sample_client):
    res = client.post("/clients", data={"name": sample_client, "program": "Beginner"},
                      follow_redirects=True)
    assert b"already exists" in res.data


def test_unknown_client_404(client):
    assert client.get("/clients/nobody").status_code == 404
    assert client.post("/clients/nobody/progress", data={"adherence": "50"}).status_code == 404


# ---------- HTML: generate program ----------
def test_generate_program_stores_plan(client, sample_client):
    from app import PROGRAM_TEMPLATES
    client.post(f"/clients/{sample_client}/generate")
    plan = client.get(f"/api/clients/{sample_client}").get_json()["generated_plan"]
    assert plan in PROGRAM_TEMPLATES["Fat Loss"]


# ---------- HTML: progress ----------
def test_add_progress(client, sample_client):
    res = client.post(f"/clients/{sample_client}/progress",
                      data={"week": "Week 1", "adherence": "85"}, follow_redirects=True)
    assert b"Progress saved" in res.data
    assert b"85%" in res.data


def test_progress_rejects_out_of_range(client, sample_client):
    res = client.post(f"/clients/{sample_client}/progress",
                      data={"adherence": "150"}, follow_redirects=True)
    assert b"0 to 100" in res.data


# ---------- HTML: workouts ----------
def test_add_workout(client, sample_client):
    res = client.post(f"/clients/{sample_client}/workouts", data={
        "date": "2026-09-26", "workout_type": "Strength", "duration_min": "60", "notes": "PR day",
    }, follow_redirects=True)
    assert b"Workout logged" in res.data
    assert b"Strength" in res.data and b"PR day" in res.data


def test_workout_requires_type(client, sample_client):
    res = client.post(f"/clients/{sample_client}/workouts",
                      data={"workout_type": ""}, follow_redirects=True)
    assert b"Enter a workout type" in res.data


# ---------- JSON API: clients ----------
def test_api_create_and_get_client(client):
    res = client.post("/api/clients", json={"name": "Kiran", "program": "Muscle Gain"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["program"] == "Muscle Gain"
    assert body["calories"] is None          # no weight yet
    assert body["membership_status"] == "N/A"

    assert client.get("/api/clients/Kiran").get_json()["name"] == "Kiran"
    assert [c["name"] for c in client.get("/api/clients").get_json()] == ["Kiran"]


def test_api_create_client_validation_error(client):
    res = client.post("/api/clients", json={"name": "Kiran", "program": "Yoga"})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_api_create_client_without_body(client):
    assert client.post("/api/clients").status_code == 400


def test_api_unknown_client_404(client):
    assert client.get("/api/clients/nobody").status_code == 404


# ---------- login ----------
def test_pages_require_login(anon_client):
    res = anon_client.get("/")
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/login")


def test_api_requires_login(anon_client):
    assert anon_client.get("/api/clients").status_code == 401


def test_login_page(anon_client):
    assert b"Staff Login" in anon_client.get("/login").data


def test_login_with_default_account(anon_client):
    res = anon_client.post("/login", data={"username": "admin", "password": "password123"},
                           follow_redirects=True)
    assert b"Add Client" in res.data


def test_login_wrong_password(anon_client):
    res = anon_client.post("/login", data={"username": "admin", "password": "wrong"},
                           follow_redirects=True)
    assert b"Invalid username or password" in res.data


def test_logout(client):
    client.post("/logout")
    assert client.get("/").status_code == 302


# ---------- profile ----------
def test_new_client_has_empty_profile(client):
    client.post("/clients", data={"name": "Asha", "program": "Beginner"})
    body = client.get("/api/clients/Asha").get_json()
    assert body["age"] is None and body["weight"] is None and body["bmi"] is None


def test_profile_update_recalculates(client, sample_client):
    client.post(f"/clients/{sample_client}/profile", data={
        "program": "Muscle Gain", "age": "31", "height": "175", "weight": "90",
    })
    body = client.get(f"/api/clients/{sample_client}").get_json()
    assert body["program"] == "Muscle Gain"
    assert body["calories"] == 90 * 35
    assert body["membership_status"] == "N/A"   # cleared because left empty


def test_profile_rejects_non_numeric_weight(client, sample_client):
    res = client.post(f"/clients/{sample_client}/profile",
                      data={"program": "Fat Loss", "weight": "abc"}, follow_redirects=True)
    assert b"must be numbers" in res.data


def test_profile_rejects_negative_values(client, sample_client):
    res = client.post(f"/clients/{sample_client}/profile",
                      data={"program": "Fat Loss", "weight": "-5"}, follow_redirects=True)
    assert b"greater than 0" in res.data


def test_profile_rejects_bad_date(client, sample_client):
    res = client.post(f"/clients/{sample_client}/profile",
                      data={"program": "Fat Loss", "membership_end": "31-12-2026"},
                      follow_redirects=True)
    assert b"valid date" in res.data


def test_profile_unknown_client_404(client):
    assert client.post("/clients/nobody/profile", data={"program": "Beginner"}).status_code == 404
