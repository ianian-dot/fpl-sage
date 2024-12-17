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
    query = '''SELECT sp.first_name || ' ' || sp.second_name as name, 
        st.short_name as team, 
        sp.now_cost, sp.total_points, 
        sp.position
    FROM StaticPlayers sp 
    JOIN StaticTeams st ON sp.team = st.id
    ORDER BY total_points DESC 
    LIMIT 5'''
    df = pd.read_sql(query, conn)
    conn.close()
    return df.to_json(orient='records')

## ENDPOINT 1.1: Top players per position based on recent form 
@app.route('/topplayers/position', methods = ['GET'])
def get_top_players_position_form():
    conn = get_db_connection()
    query = '''
    SELECT sp.position, 
            sp.first_name || ' ' || sp.second_name as name,
            st.short_name as team, 
            ROUND(AVG(ph.total_points), 1) as past_3_games_avg, --take the avg of the entire col
            now_cost/10 as cost_mil,
            ROUND(sp.total_points/(sp.now_cost/10),1) as points_per_mil,
            ict_index
    FROM PlayerHistories ph
    LEFT JOIN StaticPlayers sp ON ph.element = sp.player_id
    LEFT JOIN StaticTeams st ON sp.team = st.id
    WHERE ph.round >= (SELECT MAX(round) - 2 FROM PlayerHistories)
    GROUP BY sp.player_id --need this line since we are aggregating ph.totalpoints
    '''

    df = pd.read_sql(query, conn)
    df = df.sort_values(['position', 'past_3_games_avg'], ascending=False).groupby('position').head(3)
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

## Endpoint4: Get player history to plot player past 5 games perfomance
@app.route('/player/<int:player_id>/history', methods = ['GET'])
def get_player_hist(player_id):
    conn = get_db_connection()
    query = '''
    SELECT round, total_points, bonus
    FROM PlayerHistories 
    WHERE element = ? 
    ORDER BY round DESC
    LIMIT 5
    '''
    df = pd.read_sql(query, conn, params=(player_id,))
    conn.close()
    return df.to_json(orient='records')
    

## Endpoint3: Plot player history 
@app.route('/')
def home():
    return render_template('index.html') ##returns the html on home page 

## RUN THE APP
if __name__ == '__main__':
    app.run(debug=True)