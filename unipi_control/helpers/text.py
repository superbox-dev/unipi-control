"""Collection of text helpers."""

import re

import unicodedata


def slugify(value: str) -> str:
    """Convert to ID safe text.

    Convert to ASCII. Convert spaces to hyphens. Remove characters that aren't
    alphanumerics, underscores, or hyphens. Convert to lowercase. Also strip
    leading and trailing whitespace.

    Parameters
    ----------
    value: str
        String to slugify.

    Returns
    -------
    str
        Converted string.
    """
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "_", value)
