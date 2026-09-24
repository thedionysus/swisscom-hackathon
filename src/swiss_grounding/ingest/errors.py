"""Failures the ingest pipeline distinguishes by type."""


class EnrichmentError(Exception):
    """The model's contribution to a document was unusable.

    Empty or malformed output from the translator or the classifier, and a section that had text in
    the original but none in English. Raised rather than absorbed: the document is left out of the
    index, and because it never reaches persistence the next run fetches and asks the model again,
    which is the intended handling of a translation or tagging failure.

    Not for a document that simply holds nothing worth indexing. No retry puts chunks into a page
    that has none, so that case is a skipped outcome in `persist`, not an error raised here.
    """
