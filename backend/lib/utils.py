"""Pure utility functions for the Iris Tailor backend."""


def reverse_string(s: str) -> str:
    """Return s reversed by Unicode codepoint (standard Python slice behaviour).

    Grapheme-cluster-aware reversal (e.g. emoji sequences) is out of scope;
    callers should not rely on correct reversal of multi-codepoint grapheme
    clusters such as ZWJ sequences or combining characters.

    Raises:
        TypeError: if s is not a str instance.
    """
    if not isinstance(s, str):
        raise TypeError(f"reverse_string expects a str, got {type(s).__name__!r}")
    return s[::-1]
