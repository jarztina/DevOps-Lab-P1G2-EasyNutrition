import requests

#Initialising Spoonacular API
API_KEY = '7ce6627f3a3b43a2a3904676235b3e9c'
url = "https://api.spoonacular.com/recipes/findByIngredients"

ingredients = "diced chicken, rice, broccoli" 

params = {
    "ingredients": ingredients,  
    "number": 1,            # Number of recipes to retrieve
    "ranking": 1,           # 1 = Maximize used ingredients
    "ignorePantry": True    # Ignores basics like salt, water, oil
}

headers = {'x-api-key': API_KEY}
response = requests.get(url, headers=headers, params=params)
recipes = response.json()
print(recipes[0]["steps"])