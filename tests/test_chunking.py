from alexandria.manuals.chunking import chunk_page, chunk_pages


def test_short_page_is_a_single_chunk():
    chunks = chunk_page("Torque the bolt to 25 ft-lb.", page=5)
    assert len(chunks) == 1
    assert chunks[0].page == 5
    assert chunks[0].text == "Torque the bolt to 25 ft-lb."


def test_empty_page_produces_no_chunks():
    assert chunk_page("   ", page=1) == []
    assert chunk_page("", page=1) == []


def test_long_page_splits_into_overlapping_chunks():
    text = "word " * 500  # well over the default chunk_size
    chunks = chunk_page(text, page=10, chunk_size=200, overlap=50)
    assert len(chunks) > 1
    assert all(chunk.page == 10 for chunk in chunks)
    assert all(len(chunk.text) <= 200 for chunk in chunks)


def test_chunk_pages_assigns_1_indexed_page_numbers():
    chunks = chunk_pages(["page one text", "page two text", "page three text"])
    assert [c.page for c in chunks] == [1, 2, 3]
