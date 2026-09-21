from swiss_grounding.ingest.reclean import SourceReclean, _summarise


def test_summarise_counts_chunks_and_documents_per_source():
    rows = [
        {"source_id": "zh_ch", "document_id": 1},
        {"source_id": "zh_ch", "document_id": 1},
        {"source_id": "ch_ch", "document_id": 2},
    ]
    result = _summarise(rows, dropped_document_ids={2})
    assert result == (
        SourceReclean(source_id="ch_ch", dropped_chunks=1, dropped_documents=1),
        SourceReclean(source_id="zh_ch", dropped_chunks=2, dropped_documents=0),
    )


def test_summarise_orders_sources_alphabetically():
    rows = [
        {"source_id": "zh_ch", "document_id": 1},
        {"source_id": "ch_ch", "document_id": 2},
    ]
    result = _summarise(rows, dropped_document_ids=())
    assert [s.source_id for s in result] == ["ch_ch", "zh_ch"]


def test_summarise_counts_multiple_dropped_documents_for_one_source():
    rows = [
        {"source_id": "ch_ch", "document_id": 1},
        {"source_id": "ch_ch", "document_id": 2},
    ]
    result = _summarise(rows, dropped_document_ids={1, 2})
    assert result == (SourceReclean(source_id="ch_ch", dropped_chunks=2, dropped_documents=2),)


def test_summarise_of_no_rows_is_empty():
    assert _summarise([], dropped_document_ids=()) == ()
