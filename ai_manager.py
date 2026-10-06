import base64
import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic
from PIL import Image

load_dotenv()

client = Anthropic()

def get_image_media_type(image_path: str) -> str:
    with Image.open(image_path) as img:
        fmt = img.format.lower()
        if fmt in ["jpeg", "jpg"]:
            return "image/jpeg"
        elif fmt == "png":
            return "image/png"
        elif fmt == "webp":
            return "image/webp"
        elif fmt == "gif":
            return "image/gif"
        else:
            raise ValueError(f"Unsupported image format: {fmt}")

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")

def get_recipes_from_image(image_path: str, dietary_restrictions: list = None, allergies: list = None):
    # 1. Verify file existence before execution
    if not os.path.exists(image_path):
        print(f"Error: Could not find file '{image_path}' in {os.getcwd()}")
        return None

    dietary_restrictions_str = ", ".join(dietary_restrictions) if dietary_restrictions else "None"
    allergies_str = ", ".join(allergies) if allergies else "None"

    try:
        base64_data = encode_image(image_path)
        media_type = get_image_media_type(image_path)

        prompt = f"""
        Analyze the food ingredients in this photo.
        USER CONSTRAINTS:
        - Dietary Preferences: {dietary_restrictions_str}
        - Allergies / Exclusions: {allergies_str}

        CRITICAL RULES:
        1. Every generated recipe MUST strictly satisfy the listed Dietary Preferences (e.g., if vegetarian, no meat or poultry).
        2. NEVER include any listed allergy items in the recipes (neither as present nor missing/extra ingredients).            
        Return EXACTLY 5 recipe ideas based on these ingredients.
        
        You must return ONLY a raw JSON object with no markdown formatting, no conversational text, and no backticks. The JSON must follow this exact structure:
        {{
          "recipes": [
            {{
              "recipe_name": "Name of Recipe",
              "ingredients_present": ["item1", "item2"],
              "ingredients_missing": ["item3", "item4"],
              "instructions": ["Step 1", "Step 2"]
            }}
          ]
        }}
        """

        response = client.messages.create(
            model="claude-sonnet-5-5",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        raw_text = ""
        for block in response.content:
            if block.type == "text":
                raw_text = block.text.strip()
                break


        # Clean markdown code block wraps if present
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.replace("```", "").strip()

        return json.loads(raw_text)

    except Exception as e:
        print(f"Error executing API call: {e}")
        return None

# Safe execution block
if __name__ == "__main__":
    image_filename = "test_image.png"
    recipe_data = get_recipes_from_image(image_filename, dietary_restrictions=["vegetarian"])

    # 2. Check that dictionary data was returned before indexing
    if recipe_data and "recipes" in recipe_data:
        for index, recipe in enumerate(recipe_data["recipes"], start=1):
            print(f"Recipe {index}: {recipe['recipe_name']}")
            print(f"Present: {', '.join(recipe['ingredients_present'])}")
            print(f"Missing: {', '.join(recipe['ingredients_missing'])}")
            print(f"Instructions:")
            for step_index, step in enumerate(recipe['instructions'], start=1):
                print(f"  {step_index}. {step}")
            print("-" * 30)
    else:
        print("Failed to retrieve recipes. Please check the error messages above.")
