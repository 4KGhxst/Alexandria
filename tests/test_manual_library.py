from alexandria.manuals.manual_library import ManualLibrary
from alexandria.manuals.vehicle import Vehicle

CIVIC = Vehicle(2015, "Honda", "Civic")
ACCORD = Vehicle(2018, "Honda", "Accord")


def _library_with_civic_data() -> ManualLibrary:
    library = ManualLibrary()
    library.add_pages(
        [
            "Front wheel lug nut torque specification: 80 ft-lb.",
            "Oil drain plug torque specification: 29 ft-lb. Use a new crush washer.",
            "Spark plug gap should be set to 0.041 inches for this engine.",
        ],
        CIVIC,
        "2015 Honda Civic Factory Service Manual",
    )
    return library


def test_add_pages_returns_chunk_count():
    library = ManualLibrary()
    count = library.add_pages(["some manual text"], CIVIC, "Test Manual")
    assert count == 1


def test_has_manual_for_reflects_ingested_vehicle():
    library = _library_with_civic_data()
    assert library.has_manual_for(CIVIC)
    assert not library.has_manual_for(ACCORD)


def test_search_finds_relevant_page_with_citation():
    library = _library_with_civic_data()
    hits = library.search("lug nut torque", CIVIC)
    assert len(hits) >= 1
    assert "80 ft-lb" in hits[0].text
    assert hits[0].page == 1
    assert hits[0].manual_title == "2015 Honda Civic Factory Service Manual"


def test_search_is_scoped_to_vehicle():
    library = _library_with_civic_data()
    hits = library.search("lug nut torque", ACCORD)
    assert hits == []


def test_search_with_no_match_returns_empty():
    library = _library_with_civic_data()
    hits = library.search("windshield wiper blade replacement", CIVIC)
    assert hits == []


def test_search_with_empty_query_returns_empty():
    library = _library_with_civic_data()
    assert library.search("", CIVIC) == []
