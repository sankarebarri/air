import air
from fastapi.testclient import TestClient
from air.responses import JSONResponse


def test_create_route_decorator_get() -> None:
    app = air.Air()

    @app.get("/")
    def read_root() -> str:
        return "<h1>Hello</h1>"

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.text == "<h1>Hello</h1>"


def test_create_route_decorator_post() -> None:
    app = air.Air()

    @app.post("/create")
    def create_item() -> JSONResponse:
        return JSONResponse({"status": "created"})

    client = TestClient(app)
    response = client.post("/create")
    assert response.status_code == 200
    assert response.json() == {"status": "created"}


def test_create_route_decorator_with_response_model() -> None:
    app = air.Air()

    @app.get("/", response_class=JSONResponse)
    def get_data() -> dict[str, int]:
        return {"value": 42}

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"value": 42}
