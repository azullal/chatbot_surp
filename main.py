import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

BASE_URL = "https://dictionary.kubishi.com/api"


# ---------------------------
# WEEK 2: RETRIEVAL
# ---------------------------
def search_dictionary(query):
    response = requests.get(
        f"{BASE_URL}/search",
        params={"q": query}
    )
    return response.json()


def extract_best_entry(api_response):
    results = api_response.get("results", [])

    if not results:
        return None

    entry = results[0]
    sense = entry.get("senses", [{}])[0]

    return {
        "word": entry.get("word", ""),
        "gloss": sense.get("gloss", ""),
        "definition": sense.get("definition", "")
    }


# ---------------------------
# WEEK 3: LLM QUERY REWRITING
# ---------------------------
def rewrite_query(user_input):
    """
    This is where your prompt goes.
    It converts natural language → single dictionary keyword.
    """


    prompt = f"""
Extract the best dictionary search term.

Rules:
- Return ONLY ONE word
- If sentence contains multiple nouns, choose the most important one
- If unsure, return the main object or concept

Input: {user_input}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You extract dictionary search terms."
                },
                {
                    "role": "user",
                    "content": prompt   
                }
            ],
            temperature=0
        )

        keyword = response.choices[0].message.content.strip().lower()
        return keyword

    except Exception:
        
        return user_input.lower().strip()


# ---------------------------
# PIPELINE (Week 3)
# ---------------------------
def process_input(user_input):
    query = rewrite_query(user_input)   
    data = search_dictionary(query)      
    entry = extract_best_entry(data)

    if not entry:
        return "No dictionary entry found."

    return (
        f"- Word: {entry['word']}\n"
        f"- Gloss: {entry['gloss']}\n"
        f"- Definition: {entry['definition']}"
    )


# ---------------------------
# CHAT LOOP
# ---------------------------
def main():
    print("Owens Valley Paiute Assistant (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        print("\nBot:")
        print(process_input(user_input))
        print()


if __name__ == "__main__":
    main()