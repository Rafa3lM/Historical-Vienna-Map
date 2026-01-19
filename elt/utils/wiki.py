from urllib.parse import unquote

def extract_page_name(uri: str) -> str:
    """
    Extract page name from Vienna History Wiki URI.
    Handles both URIResolver and ExportRDF forms.
    """
    if "/Special:URIResolver/" in uri:
        page = uri.split("/Special:URIResolver/")[-1]
    elif "/Special:ExportRDF/" in uri:
        page = uri.split("/Special:ExportRDF/")[-1]
    else:
        # Fallback: last path segment
        page = uri.rsplit("/", 1)[-1]

    return unquote(page)
