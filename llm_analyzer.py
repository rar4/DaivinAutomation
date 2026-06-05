import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMAnalyzer:
    def __init__(self, interests: str, preferences: str):
        self.client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:8080/v1"),
            api_key=os.getenv("LLM_API_KEY", "not-needed")
        )
        self.model = os.getenv("LLM_MODEL", "qwen3.5:4b")
        self.preferences = preferences
        self.interests = interests

    def analyze_profile(self, profile_text: str,) -> dict:
        """
        Analyzes if the profile matches the user's type.
        Returns a dictionary with match status, score, and summary.
        """
        system_prompt = (
            f"You are a dating assistant. Your goal is to determine if a profile matches the user's preferences.\n"
            f"User Preferences: {self.preferences}\n\n"
            "Analyze the profile and respond in the following format:\n"
            "MATCH: YES/NO\n"
            "SCORE: 0-100\n"
            "SUMMARY: A brief summary of the person's key traits and interests\n"
            "INTEREST: {self.interests}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Profile: {profile_text}"}
                ],
                temperature=0
            )
            content = response.choices[0].message.content.strip()
            
            # Simple parsing of the response
            lines = content.split('\n')
            data = {}
            for line in lines:
                if ':' in line:
                    key, val = line.split(':', 1)
                    data[key.strip().upper()] = val.strip()

            return {
                "is_match": "YES" in data.get("MATCH", "").upper(),
                "score": float(data.get("SCORE", 0)),
                "summary": data.get("SUMMARY", ""),
                "interest": data.get("INTEREST", "Unknown")
            }
        except Exception as e:
            print(f"Error during LLM analysis: {e}")
            return {"is_match": False, "score": 0, "summary": "Error", "interest": "Unknown"}

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
                    {"role": "user", "content": f"Profile: {profile_text}"}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating opener: {e}")
            return "Hey! I saw your profile and thought we might get along. How's your day going?"