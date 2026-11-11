import os, logging, sys
from google import genai
from dotenv import load_dotenv

load_dotenv()
if not os.getenv('GEMINI_API_KEY'):
    logging.error('GEMINI_API_KEY not found.')
    sys.exit(1)

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

def run_agent(user_prompt: str):
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
    )
    return response.text

