import base64

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
JPEG_DATA_URL = "data:image/jpeg;base64," + base64.b64encode(JPEG).decode()


def register(client, **overrides):
    form = {"nickname": "Paul", "pin": "1234", "country_code": "CM", "rules_accepted": "true"}
    form.update(overrides)
    return client.post("/register", data=form, follow_redirects=False)


def test_register_logs_the_player_in(client):
    response = register(client)
    assert response.status_code == 303
    assert "session" in response.cookies
    home = client.get("/")
    assert "Salut Paul" in home.text and 'href="/profile"' in home.text


def test_register_error_keeps_fields_and_shows_message(client):
    response = register(client, pin="12")
    assert response.status_code == 400
    assert "exactement 4 chiffres" in response.text
    assert 'value="Paul"' in response.text
    assert "session" not in response.cookies


def test_register_without_accepting_rules_fails(client):
    response = register(client, rules_accepted="")
    assert response.status_code == 400
    assert "accepter le règlement" in response.text


def test_register_with_avatar_from_browser(client):
    register(client, avatar_data=JPEG_DATA_URL)
    user_id = 1
    avatar = client.get(f"/avatars/{user_id}")
    assert avatar.status_code == 200
    assert avatar.headers["content-type"] == "image/jpeg"
    assert avatar.content == JPEG


def test_register_with_invalid_avatar_creates_no_account(client):
    response = register(client, avatar_data="data:image/gif;base64,R0lGODlh")
    assert response.status_code == 400
    assert "JPEG ou PNG" in response.text
    assert client.get("/login").status_code == 200  # toujours déconnecté
    assert "Paul" not in client.get("/").text


def test_login_and_logout(client):
    register(client)
    client.post("/logout")
    assert "Salut Paul" not in client.get("/").text

    response = client.post("/login", data={"nickname": "paul", "pin": "1234"},
                           follow_redirects=False)
    assert response.status_code == 303
    assert "Salut Paul" in client.get("/").text


def test_login_with_wrong_pin(client):
    register(client)
    client.post("/logout")
    response = client.post("/login", data={"nickname": "Paul", "pin": "0000"})
    assert response.status_code == 400
    assert "incorrect" in response.text


def test_profile_requires_login(client):
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/profile"  # retour au profil ensuite


def test_forged_cookie_is_ignored(client):
    register(client)
    client.cookies.set("session", "1.9999999999.fausse-signature")
    assert client.get("/profile", follow_redirects=False).status_code == 303


def test_profile_update_country_and_avatar(client):
    register(client)
    response = client.post("/profile", data={"country_code": "BF", "avatar_data": JPEG_DATA_URL})
    assert "Profil enregistré" in response.text
    assert 'value="BF" selected' in response.text
    assert client.get("/avatars/1").content == JPEG


def test_profile_update_with_raw_file_upload(client):
    register(client)
    files = {"avatar_file": ("photo.jpg", JPEG, "image/jpeg")}
    client.post("/profile", data={"country_code": "CM"}, files=files)
    assert client.get("/avatars/1").content == JPEG


def test_profile_refuses_unknown_country(client):
    register(client)
    response = client.post("/profile", data={"country_code": "XX"})
    assert response.status_code == 400


def test_missing_avatar_returns_404(client):
    register(client)
    assert client.get("/avatars/1").status_code == 404
    assert client.get("/avatars/999").status_code == 404


def test_rules_page_is_public(client):
    response = client.get("/rules")
    assert response.status_code == 200
    assert "10 minutes" in response.text
