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


def test_supplemental_entries_are_last(client) -> None:
    payload = client.get("/api/v1/characters", params={"char": "不"}).json()
    assert payload["entries"][-1]["is_added"] is True
    assert payload["entries"][-1]["source_id"] == "w449b0201a"
    assert payload["entries"][-1]["definition"] == (
        "九韻甬鳩切又甫救切有韻方久切又甫救切"
    )
    assert all(not entry["is_added"] for entry in payload["entries"][:-1])


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
        "entries": 25334,
    }
    assert payload["profile"]["added_entries"] == 207
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


def test_hierarchy_search_matches_levels_independently(client) -> None:
    payload = client.get(
        "/api/v1/overview/hierarchy-search", params={"q": "東"}
    ).json()
    results = payload["results"]

    assert payload["count"] == sum(len(items) for items in results.values())
    assert any(item["label"] == "東韻" for item in results["rhymes"])
    assert any(item["label"].startswith("東小韻") for item in results["small_rhymes"])
    entry = next(item for item in results["entries"] if item["label"] == "東")
    assert entry["volume_id"]
    assert entry["rhyme_id"]
    assert entry["small_rhyme_id"]
    assert entry["entry_id"]

    volume_results = client.get(
        "/api/v1/overview/hierarchy-search", params={"q": "卷一"}
    ).json()["results"]["volumes"]
    assert volume_results[0]["label"] == "卷一 · 平聲"


def test_hierarchy_search_resolves_simplified_characters(client) -> None:
    results = client.get(
        "/api/v1/overview/hierarchy-search", params={"q": "东"}
    ).json()["results"]

    assert any(item["label"] == "東韻" for item in results["rhymes"])
    assert any(item["label"].startswith("東小韻") for item in results["small_rhymes"])
    assert any(item["label"] == "東" for item in results["entries"])

    fanqie_results = client.get(
        "/api/v1/overview/hierarchy-search", params={"q": "德红"}
    ).json()["results"]
    assert any(item["label"] == "東韻" for item in fanqie_results["rhymes"])
    assert any(
        item["label"] == "東小韻 · 德紅切"
        for item in fanqie_results["small_rhymes"]
    )


def test_hierarchy_search_excludes_supplemental_entries(client) -> None:
    payload = client.get(
        "/api/v1/overview/hierarchy-search", params={"q": "帎"}
    ).json()
    assert payload["results"]["entries"] == []


def test_rhyme_overview(client) -> None:
    payload = client.get("/api/v1/rhymes/1").json()
    assert payload["name"] == "東"
    assert payload["small_rhyme_count"] > 0
    assert payload["entry_count"] > 0
    assert payload["small_rhymes"][0]["head_character"] == "東"


def test_small_rhyme_overview_excludes_supplements(client) -> None:
    character_payload = client.get("/api/v1/characters", params={"char": "不"}).json()
    supplement = next(
        entry for entry in character_payload["entries"] if entry["is_added"]
    )
    payload = client.get(
        f"/api/v1/small-rhymes/{supplement['small_rhyme']['id']}"
    ).json()
    assert all(not entry["is_added"] for entry in payload["entries"])
    assert supplement["source_id"] not in {
        entry["source_id"] for entry in payload["entries"]
    }


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
    assert "app.css?v=28" in response.text
    assert "app.js?v=20" in response.text


def test_overview_page(client) -> None:
    response = client.get("/overview")
    assert response.status_code == 200
    assert "探索廣韻" in response.text
    assert "overview.css?v=48" in response.text
    assert "overview.js?v=58" in response.text
    assert 'id="overview-toc"' in response.text
    assert 'id="hierarchy-search-form"' in response.text
    assert 'id="hierarchy-search-input"' in response.text
    assert 'placeholder="如：卷三、支、德红、國"' in response.text
    assert 'id="hierarchy-search-results"' in response.text
    assert "整卷長度表示正文收字總量" in response.text
    assert 'id="network-touch-inspector"' in response.text
    assert response.text.count("data-overview-section") == 6
    assert 'id="network-search-form"' in response.text
    assert 'id="network-search-status"' in response.text
    assert 'id="network-search-candidates"' in response.text
    assert 'id="network-frequency"' in response.text
    assert 'id="network-fit"' in response.text
    assert 'id="network-focus-controls"' in response.text
    assert response.text.index('href="#overview-hierarchy"') < response.text.index(
        'href="#overview-rhymes"'
    )
    assert response.text.index('id="overview-hierarchy"') < response.text.index(
        'id="overview-rhymes"'
    )
    assert '<span>03</span>卷韻結構' in response.text
    assert '<span>04</span>二百零六韻' in response.text
