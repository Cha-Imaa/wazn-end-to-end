import json
import os
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

K2_API_KEY = os.getenv("K2_API_KEY")

K2_BASE_URL = "https://api.k2think.ai/v1/chat/completions"
K2_MODEL = "MBZUAI-IFM/K2-Think-v2"

PROMPT = """
Hello how are you? what's your name
"""

OUTPUT_FILE = "k2_output.txt"


def main():
    if not K2_API_KEY:
        print("ERROR: K2_API_KEY is not set.")
        return

    payload = {
        "model": K2_MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
            }
        ],
        "stream": False,
    }

    request = urllib.request.Request(
        url=K2_BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {K2_API_KEY}",
            "Content-Type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")

    except urllib.error.HTTPError as error:
        print(f"HTTP ERROR: {error.code}")
        print(error.read().decode("utf-8", errors="replace"))
        return

    except urllib.error.URLError as error:
        print(f"NETWORK ERROR: {error}")
        return

    response_json = json.loads(response_body)

    output_text = response_json["choices"][0]["message"]["content"]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(output_text)

    print(f"Saved K2 output to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()