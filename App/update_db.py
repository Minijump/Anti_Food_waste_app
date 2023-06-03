import sqlite3
import pandas as pd
import numpy as np
import random

from bs4 import BeautifulSoup

import sys


def reset_stocks():
    """
    reset the stocks table in the db
    """
    #connect to the database to get all the unique ingredients id
    conn = sqlite3.connect('../Data/Supermarket.db')
    query = "SELECT * FROM Ingredients"
    df = pd.read_sql_query(query, conn)
    ingr_id = df['id'].unique()

    #create the table stocks
    data = []
    data.extend([(id, 5, np.random.choice([1, 2])) for id in np.random.choice(ingr_id, size=300, replace=True)])
    data.extend([(id, 4, np.random.randint(1, 4)) for id in np.random.choice(ingr_id, size=500, replace=True)])
    data.extend([(id, 3, np.random.randint(1, 5)) for id in np.random.choice(ingr_id, size=800, replace=True)])
    data.extend([(id, 2, np.random.randint(1, 5)) for id in np.random.choice(ingr_id, size=800, replace=True)])
    data.extend([(id, 1, np.random.randint(1, 4)) for id in np.random.choice(ingr_id, size=600, replace=True)])
    df_stocks = pd.DataFrame(data, columns=['ingredient_id', 'urgent', 'quantity'])

    # replace the existing table
    df_stocks.to_sql('Stocks', conn, if_exists='replace', index=False)


    conn.commit()
    conn.close()


def reset_users():
    """ 
    reset the user table in the db
    """
    # connect to the database, select the ids of the different recepie
    conn = sqlite3.connect('../Data/Supermarket.db')
    query = "SELECT id FROM Recipes"
    recepie = pd.read_sql_query(query, conn)

    #create the user table
    id = np.arange(1,10001,1)
    recepie_id = np.random.choice(recepie['id'], size = 10000, replace=True)
    df_users = pd.DataFrame({'id': id, 'recepie_id': recepie_id})

    #replace the existing table in the db
    df_users.to_sql('Users', conn, if_exists='replace', index=False)


    conn.commit()
    conn.close()

def add_commands(user_id: int, recipe_id: int):
    """ 
    add a command with user_id and recipe_id to the db
    """
    #connect to the db
    conn = sqlite3.connect('../Data/Supermarket.db')

    #add a line with the command
    query = f"INSERT INTO Commands VALUES({user_id},{recipe_id})"
    conn.execute(query)

    conn.commit()
    conn.close()

def remove_html_tags(text):
    """ 
    remove the html tahs of the text
    """
    soup = BeautifulSoup(text, "html.parser")
    cleaned_text = soup.get_text()
    return cleaned_text

def pre_process_text(stop_words, punctuation, text: str)-> str:
    """ 
    the function will preprocess and return the overview
    Lowercase, delete stop words and punctuation
    """
    #specific import for this function
    from nltk.tokenize import word_tokenize

    # Tokenisation des mots
    tokens = word_tokenize(text.lower())
    # Suppression des stopwords et de la ponctuation
    tokens = [w for w in tokens if not w in stop_words and not w in punctuation]
    
    # Rejoindre les mots restants en un seul texte
    cleaned_text = " ".join(tokens)
    return cleaned_text

def reset_commands():
    """ 
    reset the commands table in db
    """
    #do the imports needed for this function
    import nltk
    from nltk.corpus import stopwords

    import string
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    # connect to the db
    conn = sqlite3.connect('../Data/Supermarket.db')

    # get the data
    query = "SELECT id, instructions, summary FROM Recipes"
    df = pd.read_sql_query(query, conn)

    # process the data from recipes
    df['instructions'] = df['instructions'].astype('str')
    df['summary'] = df['summary'].astype('str')
    df['description'] = df['summary'].apply(remove_html_tags) + df['instructions'].apply(remove_html_tags)

    # load stopwords
    nltk.download('stopwords')
    nltk.download('punkt')
    # define stopwords an punctuation to delete
    stop_words = set(stopwords.words('english'))
    punctuation = set(string.punctuation)
    # preprocess the texts
    #df['description']= df['description'].apply(pre_process_text)
    df['description']= df['description'].apply(lambda x: pre_process_text(stop_words, punctuation, x))


    #create tf-idf matrix
    description_list = df['description'].tolist()
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(description_list)

    #create cosine similarity matrix
    tfidf_matrix = tfidf_matrix.astype('float32')  #takes less time
    similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

    #get data from user table
    query = "SELECT * FROM Users"
    df_users = pd.read_sql_query(query, conn)

    # add transaction in function of user favourite recipes, tf-idf and random factor
    list_rec = []
    list_user = []
    for i in range(len(df_users)):
        #get the favourite recepie of the client
        fav_rec_id = df_users.iloc[i]['recepie_id']
        #get the client's id
        user_id = df_users.iloc[i]['id']
        
        #get the position of the recepie in the matrix
        position = df[df['id'] == fav_rec_id].index[0]

        #add the recepie that respect the treshold
        treshold = random.random()
        for r in range(len(df)):
            similarity_coef = similarity_matrix[position][r]

            if treshold < similarity_coef:
                recepie_id = df.iloc[r]['id']
                list_rec.extend([recepie_id])
                list_user.extend([user_id])
    df_command = pd.DataFrame({'user_id': list_user, 'recepie_id': list_rec })

    #replace the table in the db
    df_command.to_sql('Commands', conn, if_exists='replace', index=False)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    reset_users()
    reset_stocks()
    reset_commands()
