import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

def fetch_summary(title, authors):
    # Load environment variables
    load_dotenv()

    # Configure the Gemini API
    api_key = os.getenv("GEMINI_KEY")
    if not api_key:
        print("API key not found.")
        return

    genai.configure(api_key=api_key)
    print(f"Using API Key: {api_key}")

    # Define the prompt for the Gemini API
    prompt = f'Summarize the book "{title}" by {authors} in 5 sentences or less. If you don\'t know the book, return the word "missing" and only this word."'

    try:
        # Fetch the summary using the Gemini API
        model = genai.GenerativeModel('gemini-pro', 
            safety_settings=[
                {"category": "HARM_CATEGORY_DANGEROUS", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )

        llm_response = model.generate_content(prompt)
        
        # Check for a valid response
        if llm_response:
            summary = llm_response.text
            return summary
        else:
            # Check safety ratings if response is empty
            print(f"Response might be blocked: {llm_response.candidates[0].safety_ratings}")
            return "missing"

    except Exception as e:
        # Handle exceptions gracefully
        print(f"Error: {e}")
        return "missing"

if __name__ == "__main__":
    # Test data
    title = "1984"
    authors = "George Orwell"

    # Fetch the summary and print it
    summary = fetch_summary(title, authors)
    print(f"Summary: {summary}")
