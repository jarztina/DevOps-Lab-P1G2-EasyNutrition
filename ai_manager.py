import requests

#Initialising Spoonacular API
API_KEY = '7ce6627f3a3b43a2a3904676235b3e9c'
url = "https://api.spoonacular.com/recipes/findByIngredients"


def get_recipes(ingredients: str):

    params = {
        "ingredients": ingredients,     #Takes in a string of ingredients separated by commas
        "number": 5,                    # Number of recipes to retrieve
        "ranking": 1,                   # 1 = Maximize used ingredients
        "ignorePantry": True            # Ignores basics like salt, water, oil
    }

    headers = {'x-api-key': API_KEY}
    response = requests.get(url, headers=headers, params=params)
    recipes = response.json()

    for recipe in recipes:
        print(f"Recipe: {recipe['title']}\n")
        print("Existing Ingredients: ")
        for i in range(len(recipe['usedIngredients'])):
            print(f"    - {recipe['usedIngredients'][i]['amount']} {recipe['usedIngredients'][i]['unit']} {recipe['usedIngredients'][i]['name']}")

        print("\nAdditional Ingredients: ")
        for i in range(len(recipe['missedIngredients'])):
            print(f"    - {recipe['missedIngredients'][i]['amount']} {recipe['missedIngredients'][i]['unit']} {recipe['missedIngredients'][i]['name']}")

        print(f"\nLink: https://spoonacular.com/recipes/{recipe['title'].replace(' ', '-')}-{recipe['id']}\n\n")

get_recipes("chicken, rice, broccoli")