import re

NHI_KEYWORDS = [
    "UAP", "UFO", "alien", "aliens", "extraterrestrial", "non-human",
    "NHI", "phenomenon", "phenomena", "disclosure", "crash",
    "space", "moon", "mars", "nasa", "aerospace", "orb", "tic tac",
    "abduction", "encounter", "reverse engineering",
    "saucer", "aerial", "interstellar", "meta-material",
    "hidden tech", "whistleblower", "debrief", "men in black",
    "unidentified", "crash retrieval", "david grusch", "ross coulthart",
    "gary nolan", "angels", "demons", "angelic", "demonic", "ultraterresterial",
]

# Precompile pattern with word boundaries and optional spaces for multi-word phrases
KEYWORD_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k.lower()) for k in NHI_KEYWORDS) + r")\b", flags=re.IGNORECASE
)

def is_relevant_video(snippet):
    """
    Returns True if the video's title or description contains relevant keywords.
    """
    try:
        text = f"{snippet.get('title', '')} {snippet.get('description', '')}".lower()
        match = KEYWORD_PATTERN.search(text)
        if match:
            print(f"[MATCH] {match.group(0)} in: {text}")
        return bool(match)
    except Exception:
        return False
