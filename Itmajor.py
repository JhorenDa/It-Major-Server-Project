import mysql.connector
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import random

# FastAPI app initialization
app = FastAPI()

# Database connection setup
def get_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",  # XAMPP default username
        password="",  # No password in XAMPP
        database="recipe_db"  # Make sure this matches your database name
    )
    try:
        yield conn
    finally:
        conn.close()

# Pydantic Models for recipe representation
class RecipeBase(BaseModel):
    name: str
    category: str  # meal, breakfast, snack
    instructions: str

class RecipeCreate(RecipeBase):
    pass

class Recipe(RecipeBase):
    id: int

    class Config:
        orm_mode = True

# Database Initialization
def initialize_database():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",  # XAMPP default username
        password=""  # No password for XAMPP default setup
    )
    cursor = conn.cursor()
    
    # Create the `recipe_db` database if it doesn't exist
    cursor.execute("CREATE DATABASE IF NOT EXISTS recipe_db")
    
    # Use the `recipe_db` database
    conn.database = "recipe_db"
    
    # Create `recipes` table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(255) NOT NULL,
        instructions TEXT NOT NULL
    )
    """)
    
    cursor.close()
    conn.close()
def get_current_schedule():
    now = datetime.now()
    current_hour = now.hour

    if 6 <= current_hour < 9:
        return 'breakfast'
    elif (11 <= current_hour < 13) or (18 <= current_hour < 21):
        return 'meal'
    elif 15 <= current_hour < 17:
        return 'snack'
    else:
        return 'not time to eat'

# Call this function to initialize the database when the app starts
initialize_database()

# Routes for handling recipes

# 1. Create a new recipe
@app.post("/recipes/", response_model=Recipe)
def create_recipe(recipe: RecipeCreate, db = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO recipes (name, category, instructions) VALUES (%s, %s, %s)",
        (recipe.name, recipe.category, recipe.instructions)
    )
    db.commit()
    recipe_id = cursor.lastrowid
    cursor.close()
    
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    new_recipe = cursor.fetchone()
    cursor.close()
    return new_recipe

# 2. Get all recipes
@app.get("/recipes/", response_model=List[Recipe])
def get_all_recipes(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes")
    recipes = cursor.fetchall()
    cursor.close()
    return recipes

# 3. Get a recipe by ID
@app.get("/recipes/{recipe_id}", response_model=Recipe)
def get_recipe(recipe_id: int, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    recipe = cursor.fetchone()
    cursor.close()
    
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

# 4. Update a recipe
@app.put("/recipes/{recipe_id}", response_model=Recipe)
def update_recipe(recipe_id: int, updated_recipe: RecipeCreate, db = Depends(get_db)):
    cursor = db.cursor()
    
    # Update recipe information
    cursor.execute(
        "UPDATE recipes SET name = %s, category = %s, instructions = %s WHERE id = %s",
        (updated_recipe.name, updated_recipe.category, updated_recipe.instructions, recipe_id)
    )
    db.commit()
    
    # Fetch updated recipe
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    recipe = cursor.fetchone()
    cursor.close()
    
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

# 5. Delete a recipe
@app.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int, db = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
    db.commit()
    cursor.close()
    return {"message": f"Recipe with id {recipe_id} deleted"}

# 6. Get recipes by category (e.g., meal, breakfast, snack)
@app.get("/recipes/category/{category}", response_model=List[Recipe])
def get_recipes_by_category(category: str, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes WHERE category = %s", (category,))
    recipes = cursor.fetchall()
    cursor.close()
    return recipes

# 7. Suggest recipe based on the schedule
current_schedule = "meal"  # Default schedule

@app.get("/recipes/suggest/", response_model=Recipe)
def suggest_recipe(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes WHERE category = %s LIMIT 1", (current_schedule,))
    recipe = cursor.fetchone()
    cursor.close()
    
    if not recipe:
        raise HTTPException(status_code=404, detail="No recipes available for current schedule")
    return recipe

@app.get("/schedule/")
def get_schedule():
    current_schedule = get_current_schedule()
    return {"current_schedule": current_schedule}

@app.post("/recipes/search/", response_model=List[Recipe])
def search_recipes_by_name(name: str, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    # Search for recipes by name
    cursor.execute("SELECT * FROM recipes WHERE name LIKE %s", ('%' + name + '%',))
    recipes = cursor.fetchall()

    if not recipes:
        cursor.close()
        raise HTTPException(status_code=404, detail="No recipes found")

    # Update the views for each recipe found
    for recipe in recipes:
        cursor.execute(
            "UPDATE recipes SET views = views + 1 WHERE id = %s",
            (recipe["id"],)
        )
    
    db.commit()  # Commit the changes to the database
    cursor.close()
    return recipes


@app.get("/recipes/count/", response_model=dict)
def count_recipes_by_category(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
    SELECT category, COUNT(*) AS count 
    FROM recipes 
    GROUP BY category
    """)
    result = cursor.fetchall()
    cursor.close()
    return {category["category"]: category["count"] for category in result}

@app.get("/recipes/recent/", response_model=List[Recipe])
def get_recent_recipes(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes ORDER BY id DESC LIMIT 5")
    recipes = cursor.fetchall()
    cursor.close()
    return recipes



@app.get("/recipes/random/", response_model=Recipe)
def get_random_recipe(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes")
    recipes = cursor.fetchall()
    cursor.close()

    if not recipes:
        raise HTTPException(status_code=404, detail="No recipes found")
    return random.choice(recipes)

@app.get("/recipes/top-rated/", response_model=List[Recipe])
def get_top_rated_recipes(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes ORDER BY rating DESC LIMIT 5")
    recipes = cursor.fetchall()
    cursor.close()
    return recipes

@app.post("/recipes/{recipe_id}/rate/")
def rate_recipe(recipe_id: int, rating: int, db = Depends(get_db)):
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    cursor = db.cursor()
    cursor.execute("UPDATE recipes SET rating = %s WHERE id = %s", (rating, recipe_id))
    db.commit()
    cursor.close()
    return {"message": f"Recipe with id {recipe_id} rated {rating} stars"}

@app.get("/recipes/popular/", response_model=List[Recipe])
def get_popular_recipes(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM recipes ORDER BY views DESC LIMIT 5")
    recipes = cursor.fetchall()
    cursor.close()
    return recipes

@app.put("/recipes/favorite/", response_model=Recipe)
def update_favorite_recipe(name: str, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    
    # Check if the recipe exists
    cursor.execute("SELECT * FROM recipes WHERE name = %s", (name,))
    recipe = cursor.fetchone()

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Check if the recipe is already a favorite
    if recipe['favorite'] == 1:
        cursor.close()
        raise HTTPException(status_code=400, detail="Recipe is already in your favorite list")

    # Update the recipe to mark it as favorite
    cursor.execute("UPDATE recipes SET favorite = 1 WHERE name = %s", (name,))
    db.commit()

    # Fetch the updated recipe
    cursor.execute("SELECT * FROM recipes WHERE name = %s", (name,))
    updated_recipe = cursor.fetchone()
    cursor.close()

    return updated_recipe

@app.put("/recipes/not_favorite/", response_model=Recipe)
def update_favorite_recipe(name: str, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    
    # Check if the recipe exists
    cursor.execute("SELECT * FROM recipes WHERE name = %s", (name,))
    recipe = cursor.fetchone()

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Check if the recipe is already a favorite
    if recipe['favorite'] == 0:
        cursor.close()
        raise HTTPException(status_code=400, detail="Recipe is not in your favorite list")

    # Update the recipe to mark it as favorite
    cursor.execute("UPDATE recipes SET favorite = 0 WHERE name = %s", (name,))
    db.commit()

    # Fetch the updated recipe
    cursor.execute("SELECT * FROM recipes WHERE name = %s", (name,))
    updated_recipe = cursor.fetchone()
    cursor.close()

    return updated_recipe

@app.get("/recipes/favorites/", response_model=List[str])
def get_favorite_recipes(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    
    # Query to select all recipes that are marked as favorite
    cursor.execute("SELECT name FROM recipes WHERE favorite = 1")
    favorite_recipes = cursor.fetchall()
    cursor.close()

    # Extract recipe names from the result
    favorite_names = [recipe['name'] for recipe in favorite_recipes]
    
    return favorite_names

@app.post("/recipes/reset_views/")
def reset_all_views(db = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE recipes SET views = 0")
    db.commit()
    cursor.close()
    return {"message": "All recipe views have been reset to 0"}

@app.post("/recipes/reset_favorite/")
def reset_all_views(db = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE recipes SET favorite = 0")
    db.commit()
    cursor.close()
    return {"message": "All favorite recipe have been unfavorited."}