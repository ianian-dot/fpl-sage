from flask import Flask, jsonify, render_template
import sqlite3
import pandas as pd

app = Flask(__name__)

## Function to connect to db
def get_db_connection():
    conn = sqlite3.connect('fpl_data.db')
    conn.row_factory = sqlite3.Row ## for dictionary like access -- easier to get the items we want later
    return conn

## Endpoint1 : Get top players based on points ---
@app.route('/topplayers', methods = ['GET'])
def get_top_players():
    conn = get_db_connection()
    query = 'SELECT first_name, second_name, team, now_cost, total_points, position FROM StaticPlayers ORDER BY total_points DESC LIMIT 5'
    df = pd.read_sql(query, conn)
    conn.close()
    return df.to_json(orient='records')

## Endpoint2: Get current gameweek and deadline for setting teams 
@app.route('/gameweek', methods = ['GET'])
def get_gameweek():
    conn = get_db_connection()
    query = '''
    SELECT name as gameweek, deadline_date, deadline_time 
    FROM Fixtures 
    WHERE average_entry_score == 0
    ORDER BY gameweek
    LIMIT 1
    '''
    df = pd.read_sql(query, conn)
    conn.close()
    return df.to_json(orient='records')

## Endpoint3: Get players for dropdown 
@app.route('/players', methods = ['GET'])
def get_players_dropdown():
    conn = get_db_connection()
    query = '''
    SELECT player_id, first_name || ' ' || second_name as name, total_points
    FROM StaticPlayers
    ORDER BY total_points DESC
    LIMIT 10
    '''
    df = pd.read_sql(query, conn)
    conn.close()
    return df.to_json(orient='records')
    

## Endpoint3: Plot player history 
@app.route('/player/<int:player_id>/plot')

@app.route('/')
def home():
    return render_template('index.html')

## RUN THE APP
if __name__ == '__main__':
    app.run(debug=True)