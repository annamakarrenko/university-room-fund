def test_version_endpoint_without_release_sha(client, monkeypatch):
    monkeypatch.delenv("RELEASE_SHA", raising=False)

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "service": "university-room-fund",
        "version": "unknown",
    }


def test_version_endpoint_with_release_sha(client, monkeypatch):
    release_sha = "a" * 40
    monkeypatch.setenv("RELEASE_SHA", release_sha)

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "service": "university-room-fund",
        "version": release_sha,
    }
