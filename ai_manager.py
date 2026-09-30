import requests

#Initialising Spoonacular API
API_KEY = '7ce6627f3a3b43a2a3904676235b3e9c'
url = "https://api.spoonacular.com/recipes/findByIngredients"

ingredients = "salmon, pasta, lettuce, carrot" #placeholder to test api

params = {
    "ingredients": ingredients,  
    "number": 5,            # Number of recipes to retrieve
    "ranking": 1,           # 1 = Maximize used ingredients
    "ignorePantry": True    # Ignores basics like salt, water, oil
}

headers = {'x-api-key': API_KEY}
response = requests.get(url, headers=headers, params=params)
recipes = response.json()

for recipe in recipes:
    print(f"Recipe: {recipe['title']}")
    print(f"Used Ingredients: {[ingredient['name'] for ingredient in recipe['usedIngredients']]}")
    print(f"Missed Ingredients: {[ingredient['name'] for ingredient in recipe['missedIngredients']]}")
    print(f"Link: https://spoonacular.com/recipes/{recipe['title'].replace(' ', '-')}-{recipe['id']}\n\n")
