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


def test_character_candidates(client) -> None:
    single = client.get("/api/v1/character-candidates", params={"char": "东"}).json()
    assert single["candidates"] == [
        {"character": "东", "relation": "exact"},
        {"character": "東", "relation": "simplified-to-traditional"},
    ]

    multiple = client.get("/api/v1/character-candidates", params={"char": "发"}).json()
    assert multiple["candidates"] == [
        {"character": "发", "relation": "exact"},
        {"character": "發", "relation": "simplified-to-traditional"},
        {"character": "髮", "relation": "simplified-to-traditional"},
    ]


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


def test_overview_summary(client) -> None:
    payload = client.get("/api/v1/overview").json()
    assert payload["totals"] == {
        "volumes": 5,
        "rhymes": 206,
        "small_rhymes": 3874,
        "entries": 25541,
    }
    assert len(payload["volumes"]) == 5
    assert len(payload["rhymes"]) == 206
    assert len(payload["tone_correspondence"]) == 61
    assert payload["tone_correspondence"][0]["level"]["name"] == "東"
    assert payload["tone_correspondence"][1]["rising"]["merged"]["head_character"] == "湩"
    assert payload["tone_correspondence"][22]["rising"]["merged"]["head_character"] == "𧤛"
    assert payload["tone_correspondence"][22]["departing"]["merged"]["head_character"] == "櫬"
    assert payload["tone_correspondence"][27]["entering"]["merged"]["head_character"] == "麧"
    assert payload["tone_correspondence"][12]["kind"] == "departing-only"
    assert payload["profile"]["glyph_variant_entries"] > 0
    assert payload["largest_rhymes"]


def test_rhyme_overview(client) -> None:
    payload = client.get("/api/v1/rhymes/1").json()
    assert payload["name"] == "東"
    assert payload["small_rhyme_count"] > 0
    assert payload["entry_count"] > 0
    assert payload["small_rhymes"][0]["head_character"] == "東"


def test_fanqie_network_modes(client) -> None:
    core = client.get("/api/v1/overview/fanqie", params={"mode": "core"}).json()
    global_network = client.get(
        "/api/v1/overview/fanqie", params={"mode": "global"}
    ).json()
    assert core["node_count"] > 0
    assert core["edge_count"] > 0
    assert global_network["node_count"] >= core["node_count"]
    assert global_network["edge_count"] >= core["edge_count"]


def test_home_page(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "廣韻查詢" in response.text
    assert 'href="/overview"' in response.text
    assert "CJKVI Dictionary Database" in response.text
    assert "早稻田大學圖書館古典籍綜合資料庫" in response.text
    assert "資料：" in response.text
    assert "書影：" in response.text
    assert "簡繁：Unicode Unihan" in response.text
    assert "本站不保存或重新發布相關圖片" not in response.text
    assert 'href="/docs"' not in response.text
    assert "app.css?v=25" in response.text
    assert "app.js?v=15" in response.text


def test_overview_page(client) -> None:
    response = client.get("/overview")
    assert response.status_code == 200
    assert "探索廣韻" in response.text
    assert "overview.css" in response.text
    assert "overview.js" in response.text
    assert 'id="overview-toc"' in response.text
    assert 'id="network-touch-inspector"' in response.text
    assert response.text.count("data-overview-section") == 6
    assert 'id="network-search-form"' in response.text
    assert 'id="network-search-status"' in response.text
    assert 'id="network-search-candidates"' in response.text
    assert 'id="network-frequency"' in response.text
    assert 'id="network-fit"' in response.text
    assert 'id="network-focus-controls"' in response.text
