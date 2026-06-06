import json
import os
from typing import Literal, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()


class ProfileAnalysis(BaseModel):
    match: Literal["YES", "NO"]
    score: float = Field(ge=0, le=100)
    summary: str
    interest: str


class LLMAnalyzer:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("LLM_API_KEY", "ollama"),
        )
        self.model = "qwen3.5:4b"

    def analyze_profile(self, profile_text: str, photos: Optional[list] = None) -> dict:
        """
        Analyzes if the profile matches the user's type.
        Returns a dictionary with match status, score, and summary.
        Uses JSON schema for structured output.
        """
        # Build photo info string if photos are available
        photo_info = ""
        if photos:
            photo_info = f"\n\nPhoto Information: {len(photos)} photo(s) attached to this profile."

        system_prompt = (
            "You are a profile analyst. Your job is to identify whether a person shows genuine interest or enthusiasm in any field — broadly defined. Give people the benefit of the doubt.\n\n"
            "Analyze the provided profile text and respond ONLY with a valid JSON object. No explanation, no markdown, no preamble.\n\n"
            "**Look for positive signals (any of these count):**\n"
            "- Mentions specific projects, tools, technologies, hobbies, or communities\n"
            "- Uses domain-specific or enthusiast language\n"
            "- References learning, building, creating, or sharing — even casually\n"
            "- Shows consistent interest in a topic, even if not deeply technical\n"
            "- Any community involvement: forums, events, clubs, online groups, etc.\n"
            "- Personal passion projects, side hobbies, or creative pursuits\n"
            "- Career interest that also shows genuine curiosity or excitement\n\n"
            "**Look for negative signals (only flag if truly absent):**\n"
            "- Profile is entirely blank or content-free\n"
            '- Exclusively generic filler with zero specifics ("I love life, people, and fun")\n'
            "- No interests, topics, or activities mentioned whatsoever\n\n"
            "**Output schema (strict):**\n"
            "{\n"
            '  "match": "YES" or "NO",\n'
            '  "score": float between 0 and 100,\n'
            '  "summary": "2-3 sentence assessment of the profile",\n'
            '  "interest": "the person\'s primary field or interest, or \'unknown\' if unclear"\n'
            "}\n\n"
            "match is YES if score >= 40. Be generous and charitable — assume good faith. Most people have genuine interests even if they don't always express them eloquently. When in doubt, lean YES."
            f"{photo_info}"
        )

        try:
            response = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Profile: {profile_text}"},
                ],
                temperature=0.2,
                response_format=ProfileAnalysis,
            )
            content = response.choices[0].message.content.strip()

            print("-----------------")
            print(content)
            print("-----------------")

            # Parse JSON response
            data = json.loads(content)

            return {
                "is_match": data.get("match", "NO").upper() == "YES",
                "score": float(data.get("score", 0)),
                "summary": data.get("summary", ""),
                "interest": data.get("interest", "Unknown"),
            }
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return {
                "is_match": False,
                "score": 0,
                "summary": "Error",
                "interest": "Unknown",
            }
        except Exception as e:
            print(f"Error during LLM analysis: {e}")
            return {
                "is_match": False,
                "score": 0,
                "summary": "Error",
                "interest": "Unknown",
            }

    def generate_opener(self, profile_text: str) -> str:
        """
        Generates a personalized opener based on the profile.
        """
        system_prompt = (
            "You are a charming and witty dating assistant. "
            "Create a short, engaging ice-breaker message (max 2 sentences) based on the user's profile. "
            "Avoid generic greetings. Reference something specific from their profile to show genuine interest."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Profile: {profile_text}"},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating opener: {e}")
            return "Hey! I saw your profile and thought we might get along. How's your day going?"


if __name__ == "__main__":
    # Test with fake Russian profile data (no photos)
    test_profile = (
        "Эвелина, 18, Poznań – Mне 17, живу в Жепине, а уже в сентябре переезжаю в Познань 🌆\n"
        "Сейчас хочется найти новые знакомства, особенно очень мечтаю встретить классную подругу 🫶\n"
        "Но вообще я открыта к любому общению — люблю искренних и комфортных людей"
    )

    # Create analyzer (no arguments needed)
    analyzer = LLMAnalyzer()

    print("Testing analyze_profile with Russian profile...")
    print(f"Profile text:\n{test_profile}\n")

    try:
        result = analyzer.analyze_profile(test_profile, photos=None)
        print(f"Analysis result:")
        print(f"  is_match: {result['is_match']}")
        print(f"  score: {result['score']}")
        print(f"  summary: {result['summary']}")
        print(f"  interest: {result['interest']}")
    except Exception as e:
        print(f"Test failed with error: {e}")
