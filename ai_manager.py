import requests
import json
from PIL import Image
from google import genai
from google.genai import types

#Initialising Google GenAI API
GEMINI_API_KEY = 'AQ.Ab8RN6LfrriR03PeJ4PPOu7aYwWxclkn0U7_XdxLk2jzO_AEcA'
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

gemini_response_schema = {
    "type": "OBJECT",
    "properties": {
        "ingredients": {
            "type": "ARRAY",
            "items": {"type": "STRING"}
        }
    },
    "required": ["ingredients"]
}

#Initialising Spoonacular API
SPOONACULAR_API_KEY = '7ce6627f3a3b43a2a3904676235b3e9c'
url = "https://api.spoonacular.com/recipes/findByIngredients"

image = Image.open("test_image.png")  # To be replaced with the image captured from the camera

def get_ingredients(image) -> str:
    response = gemini_client.models.generate_content(
    model="gemini-3.8-flash",
    contents=[image,
               "Identify all food ingredients in this photo and return them as a list of strings in JSON format. Only return the list of ingredients, no other text."],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=gemini_response_schema
    )
)
    response_json = json.loads(response.text)

    return ','.join(response_json['ingredients'])  # Convert list to comma-separated string


print(get_ingredients(image)) 

def get_recipes(ingredients: str):

    params = {
        "ingredients": ingredients,     #Takes in a string of ingredients separated by commas
        "number": 5,                    # Number of recipes to retrieve
        "ranking": 1,                   # 1 = Maximize used ingredients
        "ignorePantry": True            # Ignores basics like salt, water, oil
    }

    headers = {'x-api-key': SPOONACULAR_API_KEY}
    response = requests.get(url, headers=headers, params=params)
    recipes = response.json()

    for recipe in recipes:
        print(f"Recipe: {recipe['title']}\n")
        print("Existing Ingredients: ")         #Ingredients that AI detected
        for i in range(len(recipe['usedIngredients'])):
            print(f"    - {recipe['usedIngredients'][i]['amount']} {recipe['usedIngredients'][i]['unit']} {recipe['usedIngredients'][i]['name']}")

        print("\nAdditional Ingredients: ")     #Missing Ingredients
        for i in range(len(recipe['missedIngredients'])):
            print(f"    - {recipe['missedIngredients'][i]['amount']} {recipe['missedIngredients'][i]['unit']} {recipe['missedIngredients'][i]['name']}")

        print(f"\nLink: https://spoonacular.com/recipes/{recipe['title'].replace(' ', '-')}-{recipe['id']}\n\n")

get_recipes("chicken, rice, broccoli")