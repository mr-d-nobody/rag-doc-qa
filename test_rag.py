from rag import chunk_text


def test_chunk_overlap():
    text = "a" * 2000
    chunks = chunk_text(text, size=800, overlap=150)
    assert all(len(c) <= 800 for c in chunks)
    assert len(chunks) == 4


def test_bad_overlap():
    import pytest
    with pytest.raises(ValueError):
        chunk_text("hello", size=100, overlap=100)
