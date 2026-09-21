def test_health(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_character_lookup(client) -> None:
    response = client.get("/api/v1/characters", params={"char": "東"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    first = payload["entries"][0]
    assert first["character"] == "東"
    assert first["small_rhyme"]["head_character"] == "東"
    assert first["small_rhyme"]["fanqie"] == "德紅切"
    assert first["rhyme"]["name"] == "東"
    assert first["volume"]["order"] == 1
    assert "〾" not in first["definition"]
    assert "春方也說文曰" in first["definition"]


def test_simplified_character_lookup(client) -> None:
    response = client.get("/api/v1/characters", params={"char": "东"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert payload["resolved_characters"] == ["東"]
    assert payload["entries"][0]["character"] == "東"
    assert payload["entries"][0]["matched_via"] == {
        "input_character": "东",
        "target_character": "東",
        "relation": "simplified-to-traditional",
    }


def test_one_to_many_simplified_lookup(client) -> None:
    response = client.get("/api/v1/characters", params={"char": "发"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_characters"] == ["發", "髮"]
    assert {"發", "髮"}.issubset({entry["character"] for entry in payload["entries"]})


def test_multiple_readings(client) -> None:
    response = client.get("/api/v1/characters", params={"char": "行"})
    assert response.status_code == 200
    assert response.json()["count"] > 1


def test_supplementary_plane_character(client) -> None:
    response = client.get("/api/v1/characters", params={"char": "𠍀"})
    assert response.status_code == 200
    assert response.json()["count"] >= 1


def test_missing_character_is_empty(client) -> None:
    response = client.get("/api/v1/characters", params={"char": "🙂"})
    assert response.status_code == 200
    assert response.json()["entries"] == []


def test_rejects_multiple_characters(client) -> None:
    response = client.get("/api/v1/characters", params={"char": "東冬"})
    assert response.status_code == 422


def test_browse_counts(client) -> None:
    volumes = client.get("/api/v1/volumes").json()
    rhymes = client.get("/api/v1/rhymes").json()
    assert volumes["count"] == 5
    assert rhymes["count"] == 206


def test_home_page(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "廣韻查詢" in response.text
    assert "CJKVI Dictionary Database" in response.text
