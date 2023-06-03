import sqlite3
import pandas as pd
import ast
import sys
import random

#connect to the db
conn = sqlite3.connect('../Data/Supermarket.db')

#get the data from db that will be used afterward and remains +- constant
#data from recipes
query = ("SELECT id, ingredients "
            "FROM Recipes;")
df_recipe = pd.read_sql_query(query, conn)

# A view is created with the ingredients and their product closer to expiration date
conn.execute("DROP VIEW IF EXISTS ingredients_close_expiration")
query = ("CREATE VIEW ingredients_close_expiration AS " 
        "SELECT ingredient_id, MAX(urgent) AS max_urgent " 
        "FROM Stocks " 
        "GROUP BY ingredient_id")
conn.execute(query)
conn.commit()

#number of users
query = ("SELECT COUNT(*) " 
        "FROM  Users ")
response = conn.execute(query).fetchone()
n_people = response[0]

#create a table that will store all user id that like the recipe for each recipe
conn.execute("DROP TABLE IF EXISTS id_liked_recipe")
query = ("CREATE TABLE id_liked_recipe AS "
        "SELECT recepie_id, GROUP_CONCAT(user_id, ',') AS user_ids, COUNT(user_id) AS number_id " 
        "FROM Commands " 
        "GROUP BY recepie_id;")
conn.execute(query)
conn.commit()
#add an index on recepie_id, this increase drasticly the speed
query = "DROP INDEX IF EXISTS idx_recepie_id;"
conn.execute(query)
query = "CREATE INDEX idx_recepie_id ON id_liked_recipe (recepie_id);" 
conn.execute(query)
conn.commit()



# expiration coefficient---------------------------------------------------------------------------------------------------
def extract_ingredients(row: str) -> list:
    """ 
    the function take a list of dictionnaries under the str format,
    return all the value of the keys 'id' into a list
    """
    row = ast.literal_eval(row)
    ingr_list = []

    for ingr in row:
        ingr_list.extend([ingr['id']])

    return ingr_list

def expi_coef(ingr_ids: list) -> int:
    """ 
    the function take a list of ingredients ids as input
    return the 'coefficient' of saved product
    coef = sum(urgent_column) for each ingredients
    """
    global conn

    #ask to the view the sum of expiration paramaters (for each ingredients)
    list_ingr_ids = '(' + str(ingr_ids)[1:-1] + ')' #make it a string
    query = ("SELECT SUM(max_urgent) " 
             "FROM  ingredients_close_expiration " 
             f"WHERE ingredient_id IN {list_ingr_ids}")
    coef = conn.execute(query).fetchone()

    return coef[0] if coef is not None else 0

#--------------------------------------------------------------------------------------------------------------------------
# taste coefficient------------------------------------------------------------------------------------------------------

def a_priori(n_people, recipe_id):
    """ 
    return the a priori probability 
    """
    global conn

    query = ("SELECT number_id " 
            "FROM  id_liked_recipe "
            f"WHERE recepie_id = {recipe_id}")
    response = conn.execute(query).fetchone()
    n_like_tested = response[0]

    p_like_tested = n_like_tested / n_people

    return p_like_tested


def likelihood(recipe_id, user_recipes):
    """
    return the likelihood probability 
    """

    global conn
    likelihood = 1

    query = ("SELECT number_id, user_ids "
             "FROM id_liked_recipe " 
             f" WHERE recepie_id = {recipe_id};")
    response = conn.execute(query).fetchone()
    liked_recipe_i = response[0]
    users_id_recipe_i = list(response[1].split(','))

    for recipe in user_recipes:

        query = ("SELECT user_ids " 
                "FROM  id_liked_recipe "
                f"WHERE recepie_id = {recipe}")
        response = conn.execute(query).fetchone()
        user_id_other_recipe = list(response[0].split(','))


        common_elements = set(users_id_recipe_i) & set(user_id_other_recipe)
        liked_both = len(common_elements)

        likelihood *= (1 + liked_both) / (liked_recipe_i)

    return likelihood


def taste_coef(user_recipes: list, recipe_id: int) ->float:
    """  
    return a probability that the user like the recipe of id 'recipe_id'
    """
    global conn, n_people

    #compute the 2 coeficients
    p_a_priori = a_priori(n_people, recipe_id) 
    likely = likelihood(recipe_id, user_recipes) 
    
    return p_a_priori * likely

#----------------------------------------------------------------------------------------------------------------------------------------------- 
def get_recommendation(id_user):
    """  
    update the table df_recipe with a suggestion coefficient 
    for each recipe and for user id = 'id_user'.
    """
    #use the global variables defined earlier
    global conn
    global df_recipe

    #extract ingredients
    df_recipe['ingredients'] = df_recipe['ingredients'].apply(extract_ingredients)

    # recipe id the user already liked will remains constant too
    query = ("SELECT recepie_id " 
            "FROM  Commands "
            f"WHERE user_id = {id_user}")
    response = conn.execute(query).fetchall()
    user_recipes = [row[0] for row in response]
    if len(user_recipes) > 15: #takes only 15 results, else it would be too long
        user_recipes = random.sample(user_recipes, 15)

    #compute the 2 coefficients
    df_recipe['saved_coef'] = df_recipe['ingredients'].apply(expi_coef)   #coefficient that compute the number of product saved from expiration
    df_recipe['taste_coef'] = df_recipe['id'].apply(lambda x: taste_coef(user_recipes, x)) #coefficient that compute how much the recipe will please the user

    #normalize the 2 coefficients
    df_recipe['saved_coef'] = (df_recipe['saved_coef'] - df_recipe['saved_coef'].min()) / (df_recipe['saved_coef'].max() - df_recipe['saved_coef'].min())/2 #/2 to balance coefs
    df_recipe['taste_coef'] = (df_recipe['taste_coef'] - df_recipe['taste_coef'].min()) / (df_recipe['taste_coef'].max() - df_recipe['taste_coef'].min())
    #create a suggestion_coefficient
    df_recipe['suggestion_coef'] = df_recipe['saved_coef'] + df_recipe['taste_coef']

    #close connection to database and return the recipe
    conn.commit()
    conn.close()


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Please provide the user ID")
    else:
        id = sys.argv[1]
        get_recommendation(id)

        recommendation = df_recipe[df_recipe["suggestion_coef"] == df_recipe["suggestion_coef"].max()]
        print(recommendation)  


