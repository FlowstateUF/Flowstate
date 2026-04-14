from sentence_transformers import SentenceTransformer

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed a list of texts. Returns a list of vectors."""
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()

def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]