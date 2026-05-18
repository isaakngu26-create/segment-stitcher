import difflib


def _normalize(text):
    return " ".join(str(text).lower().split())


def detect_changes(filings, definitions):
    changes = []
    reference = {}

    sorted_filings = sorted(filings, key=lambda item: item.get("period", ""))
    for filing in sorted_filings:
        filename = filing["filename"]
        current = definitions.get(filename, {})

        for segment, definition in current.items():
            previous = reference.get(segment)
            if previous and _normalize(previous) != _normalize(definition):
                ratio = difflib.SequenceMatcher(None, _normalize(previous), _normalize(definition)).ratio()
                changes.append({
                    "segment": segment,
                    "filename": filename,
                    "previous_definition": previous,
                    "current_definition": definition,
                    "similarity": round(ratio, 3),
                })

        reference.update(current)

    return changes
