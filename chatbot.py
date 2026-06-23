import os
import requests

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

BASE_URL = "https://dictionary.kubishi.com/api"


def rewrite_query(user_input):
    """
    Converts a natural language question into a simple dictionary search term.
    Example:
    'What is the Paiute word for water?' -> 'water'
    """

    text = user_input.lower().strip()

    # Common pattern: "Paiute word for water"
    if "word for" in text:
        return text.split("word for")[-1].strip(" ?.!")

    # Common pattern: "how do you say water"
    if "say" in text:
        return text.split("say")[-1].strip(" ?.!")

    # Common pattern: "what does puni mean"
    if "what does" in text and "mean" in text:
        return (
            text.replace("what does", "")
            .replace("mean", "")
            .strip(" ?.!'\"")
        )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract only the English word or Paiute word being searched. "
                        "Do not return words like Paiute, Owens Valley, language, or word."
                    ),
                },
                {
                    "role": "user",
                    "content": user_input,
                },
            ],
        )

        return response.choices[0].message.content.strip()

    except Exception:
        return user_input.lower().strip()


def search_dictionary(query):
    """
    Searches the Owens Valley Paiute dictionary API.
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


def extract_best_entry(api_response):
    """
    Extracts the best dictionary entry from the API response.
    """

    if not api_response:
        return None

    results = api_response.get("results", [])

    if not results:
        return None

    entry = results[0]
    senses = entry.get("senses", [])

    first_sense = senses[0] if senses else {}

    return {
        "word": entry.get("word", "Unknown"),
        "gloss": first_sense.get("gloss", "No gloss available"),
        "definition": first_sense.get("definition", "No definition available"),
    }


def process_input(user_input):
    if not user_input or not user_input.strip():
        return None

    search_term = rewrite_query(user_input)

    api_response = search_dictionary(search_term)

    entry = extract_best_entry(api_response)

    if entry:
        entry["search_term"] = search_term

    return entry