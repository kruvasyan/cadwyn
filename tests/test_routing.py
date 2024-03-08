from datetime import date

import pytest
from fastapi import Response
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Match, NoMatchFound, Route
from starlette.testclient import TestClient

from cadwyn import Cadwyn
from cadwyn.structure.versions import Version, VersionBundle
from tests._resources.app_for_testing_routing import mixed_hosts_app


def test__header_routing():
    client = TestClient(mixed_hosts_app, headers={"X-API-VERSION": "2022-02-11"})

    response = client.get("/v1/users/tom/83")
    assert response.status_code == 200
    assert response.json() == {"users": [{"username": "tom", "page": 83}]}

    response = client.get("/v1/")
    # its fine, because "/v1/" is defined in the lower version
    assert response.status_code == 200

    client = TestClient(mixed_hosts_app, headers={"X-API-VERSION": "2022-01-10"})

    response = client.get("/v1/users")
    assert response.status_code == 200
    assert response.text == "All users"

    response = client.get("/v1/")
    assert response.status_code == 200

    client = TestClient(mixed_hosts_app, headers={"X-API-VERSION": "2022-03-12"})

    response = client.get("/v1/users")
    # its fine, because /users is defined in the lower version
    assert response.status_code == 200

    response = client.get("/v1/")
    assert response.status_code == 200

    client = TestClient(mixed_hosts_app, headers={"X-API-VERSION": "2025-01-01"})

    response = client.get("/v1/users")
    # its fine, because /users is defined in the lower version
    assert response.status_code == 200


@pytest.mark.parametrize("version", ["2022-04-19", "2022-05-01", "2025-11-12"])
def test__host_routing__backward__ok(version: str):
    client = TestClient(mixed_hosts_app, headers={"X-API-VERSION": version})

    response = client.get("/v1/doggies/tom")
    assert response.status_code == 200
    assert response.json() == {"doggies": [{"dogname": "tom"}]}


def test__host_routing__lowest_version__404():
    client = TestClient(mixed_hosts_app, headers={"X-API-VERSION": "1993-11-15"})

    response = client.get("/v1/doggies/tom")
    assert response.status_code == 404


def test__host_routing__non_http():
    assert mixed_hosts_app.routes[-1].matches({"type": "websocket", "path": "/v1/"}) == (Match.NONE, {})


def test__host_routing__non_date_api_version_header__not_valid_format():
    client = TestClient(mixed_hosts_app, headers={"X-API-VERSION": "2025-40-01"})

    response = client.get("/v1/users")
    assert response.status_code == 422
    assert response.json()[0]["loc"] == ["header", "x-api-version"]


def test__host_routing__partial_match__error():
    client = TestClient(mixed_hosts_app, headers={"X-API-VERSION": "2022-02-11"})

    response = client.post("/v1/users/tom/83")
    assert response.status_code == 405


def test__url_path_for__not_enough_params__error():
    with pytest.raises(NoMatchFound, match='No route exists for name "api:users" and params "username".'):
        mixed_hosts_app.url_path_for("api:users", username="tom")


def test__url_path_for__not_enough_params__error2():
    with pytest.raises(NoMatchFound, match='No route exists for name "api" and params "path, username".'):
        mixed_hosts_app.url_path_for("api", path="hellow", username="tom")


def test__lifespan_async():
    startup_complete = False
    shutdown_complete = False

    async def hello_world(request: Request):
        return PlainTextResponse("hello, world")

    async def run_startup():
        nonlocal startup_complete
        startup_complete = True

    async def run_shutdown():
        nonlocal shutdown_complete
        shutdown_complete = True

    app = Cadwyn(
        versions=VersionBundle(Version(date(2022, 11, 16))),
        on_startup=[run_startup],
        on_shutdown=[run_shutdown],
    )
    app.add_unversioned_routes(Route("/v1/", hello_world))

    assert not startup_complete
    assert not shutdown_complete
    with TestClient(app) as client:
        assert startup_complete
        assert not shutdown_complete
        client.get("/v1/")
    assert startup_complete
    assert shutdown_complete


def test__host_routing__partial_match__404():
    client = TestClient(mixed_hosts_app, headers={"X-API-VERSION": "1998-11-16"})

    response = client.get("/v1/doggies/tom")
    assert response.status_code == 200


def test__fwefefe():
    app = Cadwyn(versions=VersionBundle(Version(date(2000, 1, 1))))

    @app.post("/post")
    async def post():
        return "post"

    @app.get("/get")
    async def get():
        return "get"

    @app.patch("/patch")
    async def patch():
        return "patch"

    @app.delete("/delete")
    async def delete():
        return "delete"

    @app.put("/put")
    async def put():
        return "put"

    @app.options("/options")
    async def options():
        return "options"

    @app.head("/head")
    async def head():
        return "head"

    @app.api_route("/api_route", methods=["POST"])
    async def api_route():
        return "api_route"

    async def add_api_route():
        return Response("add_api_route")

    app.add_api_route("/add_api_route", add_api_route, methods=["POST"])

    client = TestClient(app)

    standard_methods = ("post", "get", "patch", "delete", "put", "options")
    for method in standard_methods:
        response = getattr(client, method)("/" + method)
        assert response.status_code == 200, response.content
        assert response.content == f'"{method}"'.encode()

    response = client.head("/head")
    assert response.status_code == 200, response.content
    assert response.content == b""

    response = client.post("/api_route")
    assert response.status_code == 200, response.content
    assert response.content == b'"api_route"'

    response = client.post("/add_api_route")
    assert response.status_code == 200, response.content
    assert response.content == b"add_api_route"
