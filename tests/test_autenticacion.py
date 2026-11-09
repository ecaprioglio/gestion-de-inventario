from tests.conftest import ADMIN, CLAVE_DEMO, login


def test_login_correcto_entrega_token(client):
    r = client.post("/auth/login", json={"username": ADMIN[0], "password": ADMIN[2]})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_password_se_guarda_con_hash_y_no_en_texto_plano(client, tokens, db):
    fila = db.execute("SELECT password_hash FROM usuarios WHERE username = 'vendedor1'").fetchone()
    assert fila["password_hash"].startswith("scrypt$")
    assert CLAVE_DEMO not in fila["password_hash"]


def test_mismo_hash_distinto_por_sal(client, tokens, db):
    # vendedor1 y vendedor2 tienen la misma clave, pero el hash es distinto
    h = [f[0] for f in db.execute(
        "SELECT password_hash FROM usuarios WHERE username IN ('vendedor1','vendedor2')")]
    assert h[0] != h[1]


def test_mensaje_igual_para_usuario_inexistente_y_clave_mala(client):
    a = client.post("/auth/login", json={"username": "noexiste", "password": "x"})
    b = client.post("/auth/login", json={"username": ADMIN[0], "password": "mala"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_bloqueo_tras_5_intentos_fallidos(client):
    for _ in range(5):
        client.post("/auth/login", json={"username": ADMIN[0], "password": "mala"})
    r = client.post("/auth/login", json={"username": ADMIN[0], "password": ADMIN[2]})
    assert r.status_code == 429


def test_sin_token_es_rechazado(client):
    assert client.get("/productos").status_code == 401


def test_token_inventado_es_rechazado(client):
    r = client.get("/productos", headers={"Authorization": "Bearer inventado123"})
    assert r.status_code == 401


def test_token_se_guarda_como_hash(client, db):
    h = login(client, ADMIN[0], ADMIN[2])
    token = h["Authorization"].split()[1]
    filas = [f[0] for f in db.execute("SELECT token_hash FROM sesiones")]
    assert token not in filas and len(filas) == 1


def test_logout_invalida_el_token(client):
    h = login(client, ADMIN[0], ADMIN[2])
    assert client.post("/auth/logout", headers=h).status_code == 204
    assert client.get("/auth/yo", headers=h).status_code == 401


def test_password_debil_es_rechazada(client, tokens):
    r = client.post("/usuarios", headers=tokens["administrador"], json={
        "username": "debil", "email": "debil@ejemplo.cl", "password": "123", "rol": "vendedor"})
    assert r.status_code == 422


def test_cambiar_password_propia(client, tokens):
    r = client.put("/auth/yo/password", headers=tokens["vendedor"],
                   json={"actual": CLAVE_DEMO, "nueva": "NuevaClave2027"})
    assert r.status_code == 204
    login(client, "vendedor1", "NuevaClave2027")
