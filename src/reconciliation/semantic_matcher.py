from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _normalize(text):
    return " ".join(str(text).lower().split())


def match_segments(tables, definitions, threshold=0.35):
    all_definitions = []
    definition_labels = []

    for defs in definitions.values():
        for label, definition in defs.items():
            normalized = f"{label} {definition}"
            definition_labels.append(label)
            all_definitions.append(normalized)

    if not all_definitions:
        return {}

    segment_labels = []
    for table in tables.values():
        segment_labels.extend(table.get("segments", []))

    if not segment_labels:
        return {}

    corpus = [ _normalize(text) for text in segment_labels + all_definitions ]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit(corpus)
    segment_vectors = vectorizer.transform([_normalize(label) for label in segment_labels])
    definition_vectors = vectorizer.transform([_normalize(text) for text in all_definitions])
    similarity = cosine_similarity(segment_vectors, definition_vectors)

    mapping = {}
    for i, segment in enumerate(segment_labels):
        row = similarity[i]
        best_idx = int(row.argmax())
        score = float(row[best_idx])
        canonical = definition_labels[best_idx] if score >= threshold else segment
        mapping[segment] = canonical

    return mapping
