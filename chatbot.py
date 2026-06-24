import os
import re
import json
import requests

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = "https://dictionary.kubishi.com/api"

def get_openai_api_key():

    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        return api_key 

    try:
        import streamlit as st
        return st.secrets.get("OPENAI_API_KEY")
    except Exception:
        return None


api_key = get_openai_api_key()

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY not found. "
        "Add it to a .env file or to .streamlit/secrets.toml."
    )


client = OpenAI(api_key=api_key)

TOPIC_FALLBACKS = {
    "animals": ["dog", "horse", "rabbit", "fish", "bird", "deer"],
    "animal": ["dog", "horse", "rabbit", "fish", "bird", "deer"],
    "food": ["food", "water", "meat", "fish", "eat", "drink"],
    "family": ["mother", "father", "daughter", "son", "child", "woman", "man"],
    "nature": ["water", "mountain", "tree", "sun", "moon", "fire", "wind"],
}

def classify_request(user_input):
    """
    Decide what type of request the user is making.
    """
    text = user_input.lower()

    if any(
        phrase in text
        for phrase in ["example sentence", "example sentences", "use in a sentence", "sentence for", "sentences for",]
    ):
        return "sentences"
    if any(phrase in text for phrase in ["paiute sentence", "full sentence", "translated sentence",]
    ):
        return "verified_sentence"
    
    if any(word in text for word in ["list", "words related", "vocabulary", "vocab",]):
        return "word_list"

    if any(word in text for word in ["sentence", "sentences", "use in a sentence",]):
        return "sentences"

    if any(word in text for word in ["slide", "slides", "presentation", "lesson",]):
        return "slides"

    return "lookup"


def extract_topic(user_input):
    """
    Extract the topic from a vocabulary list request.
    """
    text = user_input.lower().strip()

    remove_phrases = [
        "provide me with",
        "give me",
        "make",
        "create",
        "list",
        "a list of",
        "vocabulary",
        "words",
        "word list",
        "related to",
        "about",
        "lesson",
        "slides",
        "slide",
    ]

    for phrase in remove_phrases:
        text = text.replace(phrase, "")

    text = text.strip(" ?.!")
    
    if "animal" in text:
        return "animals"
    if "food" in text:
        return "food"
    if "family" in text:
        return "family"
    if "nature" in text:
        return "nature"

    return text

def generate_topic_words(topic, count=8):

    topic = topic.lower().strip()

    if topic in TOPIC_FALLBACKS:
        return TOPIC_FALLBACKS[topic][:count]
    
    prompt = f"""
Generate {count} simple English dictionary search terms related to the topic "{topic}".

Rules:
- Return only JSON.
- Use common beginner vocabulary.
- Use single words when possible.
- Do not include explanations.

Example:
["water", "fish", "eat"]
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You generate simple English vocabulary search terms.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
        )

        content = response.choices[0].message.content.strip()
        words = json.loads(content)

        if isinstance(words, list):
            return words[:count]

    except Exception as error:
        print(f"Topic word generation error: {error}")

    return [topic]


def rewrite_query(user_input):
    """
    Extract the main search term from the user's question.
    """
    text = user_input.lower().strip()

    if "word for" in text:
        return text.split("word for")[-1].strip(" ?.!")

    if "what does" in text and "mean" in text:
        return (
            text.replace("what does", "")
            .replace("mean", "")
            .strip(" ?.!'\"")
        )

    if "sentences for" in text:
        return text.split("sentences for")[-1].strip(" ?.!")

    if "sentence for" in text:
        return text.split("sentence for")[-1].strip(" ?.!")

    if "examples for" in text:
        return text.split("examples for")[-1].strip(" ?.!")

    if "example sentences for" in text:
        return text.split("example sentences for")[-1].strip(" ?.!")

    if "say" in text:
        return text.split("say")[-1].strip(" ?.!")

    words = re.findall(r"[a-zA-Z]+", text)

    stop_words = {
        "what", "is", "the", "paiute", "word", "for", "how", "do",
        "you", "say", "in", "owens", "valley", "mean", "does",
        "give", "me", "create", "make", "list", "related", "to",
        "about", "sentence", "sentences", "slides", "lesson"
    }

    useful_words = [word for word in words if word not in stop_words]

    if useful_words:
        return useful_words[-1]

    return text


def search_dictionary(query):
    """
    Search the dictionary API.
    """
    try:
        response = requests.get(
            f"{BASE_URL}/search",
            params={"q": query},
            timeout=10,
        )

        response.raise_for_status()
        return response.json()

    except Exception as error:
        print(f"Dictionary search error: {error}")
        return None

def search_example_sentences(query, limit=20):
    """
    Search verified example sentences from the dictionary API.
    """

    try:
        response = requests.get(
            f"{BASE_URL}/search-sentences",
            params={
                "q": query,
                "limit": limit,
            },
            timeout=10,
        )

        response.raise_for_status()
        return response.json()

    except Exception as error:
        print(f"Example sentence search error: {error}")
        return None
    
def format_api_example_sentences(example_response, search_term, entry):
    """
    Format example sentences returned from the API.
    """

    if not example_response:
        return None

    results = example_response.get("results", [])

    if not results:
        return None

    response = f"""
## Example Sentences for `{search_term}`

**Dictionary word:** {entry.get("word", "Unknown")}

**Definition:** {entry.get("definition", "No definition available")}

These examples were retrieved from the verified dictionary example sentence database.

"""

    for index, example in enumerate(results[:5], start=1):
        paiute = example.get("text", "No Paiute sentence provided.")
        english = example.get("translation", "No English translation provided.")

        response += f"""
### Example {index}

**Paiute:** {paiute}

**English:** {english}

"""

    return response

def extract_best_entry(api_response):
    """
    Select the best dictionary entry from the API response.
    """
    if not api_response:
        return None

    results = api_response.get("results", [])

    if not results:
        return None

    entry = results[0]
    senses = entry.get("senses", [])
    first_sense = senses[0] if senses else {}

    glossary = first_sense.get("glossary")
    definition = first_sense.get("definition")

    return {
        "word": entry.get("word", "Unknown"),
        "glossary": glossary or "No glossary available",
        "definition": definition or "No definition available",
        "raw": entry,
    }

def format_entry(entry):
    """
    Convert a dictionary entry into a nice Markdown response.
    """
    meaning = entry.get("glossary")

    if not meaning or meaning == "No glossary available":
        meaning = entry.get("definition", "No meaning available")

    return f"""
## Dictionary Result

**Search term:** `{entry.get("search_term", "Unknown")}`

**Paiute word:** {entry.get("word", "Unknown")}

**Meaning:** {meaning}

**Definition:** {entry.get("definition", "No definition available")}
"""

def lookup_word(user_input):
    """
    Look up one dictionary word.
    """

    search_term = rewrite_query(user_input)
    api_response = search_dictionary(search_term)
    entry = extract_best_entry(api_response)

    if entry:
        entry["search_term"] = search_term
        return entry

    return None

def format_example_sentences(examples, search_term, entry):
    """
    Format verified example sentences from examples.json.
    """

    response = f"""
## Example Sentences for `{search_term}`

**Dictionary word:** {entry.get("word", "Unknown")}

**Definition:** {entry.get("definition", "No definition available")}

These examples come from the verified local example sentence database.

"""

    for index, example in enumerate(examples, start=1):
        response += f"""
### Example {index}

**Paiute:** {example.get("paiute", "No Paiute sentence provided.")}

**English:** {example.get("english", "No English translation provided.")}

"""
    return response

def build_sentences(user_input):
    """
    Retrieve verified example sentences from the dictionary sentence API.
    """

    search_term = rewrite_query(user_input)

    api_response = search_dictionary(search_term)
    entry = extract_best_entry(api_response)

    if not entry:
        return f"""
## No Example Sentence Found

I could not find a dictionary entry for `{search_term}`.
"""

    dictionary_word = entry.get("word", "")

    # First search examples with the user's English/Paiute query.
    example_response = search_example_sentences(search_term, limit=20)

    formatted_examples = format_api_example_sentences(
        example_response=example_response,
        search_term=search_term,
        entry=entry,
    )

    if formatted_examples:
        return formatted_examples

    # If nothing is found, try searching examples with the Paiute dictionary word.
    if dictionary_word:
        example_response = search_example_sentences(dictionary_word, limit=20)

        formatted_examples = format_api_example_sentences(
            example_response=example_response,
            search_term=search_term,
            entry=entry,
        )

        if formatted_examples:
            return formatted_examples

    return f"""
## No Verified Example Sentence Found

I found the dictionary entry, but I could not find verified example sentences from the sentence API.

**Search term:** `{search_term}`

**Dictionary word:** {dictionary_word}

**Definition:** {entry.get("definition", "No definition available")}
"""

def explain_verified_sentence(user_input):
    """
    Explain one verified sentence retrieved from the sentence API.
    """

    search_term = rewrite_query(user_input)

    api_response = search_dictionary(search_term)
    entry = extract_best_entry(api_response)

    if not entry:
        return f"""
## No Verified Sentence Found

I could not find a dictionary entry for `{search_term}`.
"""

    dictionary_word = entry.get("word", "")

    example_response = search_example_sentences(search_term, limit=1)
    results = example_response.get("results", []) if example_response else []

    if not results and dictionary_word:
        example_response = search_example_sentences(dictionary_word, limit=1)
        results = example_response.get("results", []) if example_response else []

    if not results:
        return f"""
## No Verified Sentence Found

I found the dictionary entry for `{search_term}`, but I could not find a verified sentence from the sentence API.
"""

    example = results[0]

    prompt = f"""
You are helping explain a verified Owens Valley Paiute example sentence.

Use ONLY the information below.
Do not invent new Paiute words.
Do not create a new Paiute sentence.
Do not claim grammar rules unless they are directly visible from the sentence.

Dictionary entry:
Search term: {search_term}
Paiute word: {entry.get("word")}
Definition: {entry.get("definition")}

Verified example sentence:
Paiute: {example.get("text")}
English: {example.get("translation")}

Explain the sentence carefully.
Include:
- the dictionary word
- the sentence
- the English translation
- a cautious explanation of what can be observed
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You explain retrieved Owens Valley Paiute examples carefully. "
                    "You do not invent grammar, words, or new sentences."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    return response.choices[0].message.content.strip()

def format_verified_sentence(sentence_data):
    return f"""
## Verified Example Sentence

**Search term:** `{sentence_data["search_term"]}`

**Dictionary word:** {sentence_data["word"]}

**Meaning:** {sentence_data["glossary"]}

**Paiute sentence:** {sentence_data["paiute_sentence"]}

**English translation:** {sentence_data["english_translation"]}

This sentence was retrieved from the source data.
"""

def build_word_list(topic):
    """
    Build a vocabulary list using dictionary API lookups.
    """

    search_terms = generate_topic_words(topic)
    entries = []

    for term in search_terms:
        api_response = search_dictionary(term)
        entry = extract_best_entry(api_response)

        if entry:
            entry["search_term"] = term
            entries.append(entry)

    if not entries:
        return f"""
## No Vocabulary Found

I could not find vocabulary for `{topic}`.
"""

    response = f"## Vocabulary List: {topic.title()}\n\n"
    response += f"Generated search terms: `{', '.join(search_terms)}`\n\n"

    for entry in entries:
        meaning = entry.get("glossary")

        if not meaning or meaning == "No glossary available":
            meaning = entry.get("definition", "No meaning available")

        response += f"- **{entry['word']}** — {meaning}\n"
        response += f"  - Search term: `{entry['search_term']}`\n"
        response += f"  - Definition: {entry['definition']}\n\n"

    return response

def build_slides(user_input):
    """
    Create a simple lesson outline from retrieved vocabulary only.
    """

    topic = extract_topic(user_input)
    vocab = build_word_list(topic)

    if not vocab:
        return f"""
## No Slides Created

I could not find vocabulary for `{topic}`.
"""

    prompt = f"""
Create a simple 4-slide lesson outline using this vocabulary content:

{vocab}

Format:
Slide 1: Title and learning goal
Slide 2: Vocabulary words
Slide 3: Practice activity
Slide 4: Review question

Rules:
- Do not invent new Paiute words.
- Use only the vocabulary shown in the retrieved content.
- Keep it classroom-friendly.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You create simple educational slide outlines "
                    "from retrieved vocabulary only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    return response.choices[0].message.content.strip()

def process_input(user_input):
    intent = classify_request(user_input)

    if intent == "verified_sentence":
        content = explain_verified_sentence(user_input)

    elif intent == "word_list":
        topic = extract_topic(user_input)
        content = build_word_list(topic)

    elif intent == "sentences":
        content = build_sentences(user_input)

    elif intent == "slides":
        content = build_slides(user_input)

    else:
        entry = lookup_word(user_input)

        if entry:
                content = format_entry(entry)
        else:
            search_term = rewrite_query(user_input)
            content = f"""
## No Dictionary Result Found

I searched for `{search_term}`, but I could not find a matching dictionary entry.
"""

    if content:
        return content

    return """
## No Response Generated

I could not generate a response for that request. Try asking for a specific Paiute word, English word, vocabulary list, or verified example sentence.
"""

from chatbot import search_dictionary
import json

data = search_dictionary("water")
print(json.dumps(data, indent=2, ensure_ascii=False))