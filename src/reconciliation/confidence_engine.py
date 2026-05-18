from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def score_match(segment, definition):
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    vectors = vectorizer.fit_transform([segment, definition])
    score = float(cosine_similarity(vectors[0:1], vectors[1:2])[0, 0])
    return score
