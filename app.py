from flask import Flask, jsonify, render_template, request
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
        st.team_name as team, 
        sp.now_cost, sp.total_points, 
        sp.position
    FROM StaticPlayers sp 
    JOIN StaticTeams st ON sp.team = st.team_id
    ORDER BY total_points DESC 
    LIMIT 5'''
    df = pd.read_sql(query, conn)


    conn.close()
    return df.to_json(orient='records')


## ENDPOINT: MOST VALUABLE PLAYERS BELOW A CERTAIN  PRICE
@app.route('/topplayersvalue', methods = ['GET'])
def get_most_val_players():
    conn = get_db_connection()
    price_thresh = float(request.args.get('price', 6))
    if price_thresh is None or price_thresh <= 0: 
        return jsonify({'error': 'Invalid price selected'})
    query = f'''SELECT sp.first_name || ' ' || sp.second_name as name, 
        st.team_name as team, 
        sp.total_points/(sp.now_cost/10) as value,
        sp.now_cost/10 as cost_mil, 
        sp.total_points, 
        sp.position
    FROM StaticPlayers sp 
    JOIN StaticTeams st ON sp.team = st.team_id
    WHERE sp.now_cost < {price_thresh*10}
    ORDER BY value DESC 
    LIMIT 5'''
    df = pd.read_sql(query, conn)


    conn.close()
    return df.to_json(orient='records')


## ENDPOINT 1.1: Top players per position based on recent form 
@app.route('/topplayers/position', methods = ['GET'])
def get_top_players_position_form():
    conn = get_db_connection()
    limit = int(request.args.get('limit', 3)) ## defaults to 3 players per pos
    query = '''
    SELECT sp.position, 
            sp.first_name || ' ' || sp.second_name as name,
            st.team_name as team, 
            ROUND(AVG(ph.total_points), 1) as past_3_games_avg, --take the avg of the entire col
            ROUND(AVG(ph.ict_index), 1) as past_3_ICT_avg, --take the avg of the entire col
            ROUND(((sp.now_cost)/AVG(ph.total_points)), 1) as recent_value,
            sp.now_cost/10 as cost_mil,
            sp.total_points as total_points,
            sp.total_points/(sp.now_cost/10) as value 
    FROM PlayerHistories ph
    LEFT JOIN StaticPlayers sp ON ph.element = sp.player_id
    LEFT JOIN StaticTeams st ON sp.team = st.team_id
    WHERE ph.round >= (SELECT MAX(round) - 2 FROM PlayerHistories)
    GROUP BY sp.player_id --need this line since we are aggregating ph.totalpoints
    '''

    df = pd.read_sql(query, conn)
    conn.close()
    df = df.sort_values(['position', 'past_3_games_avg'], ascending=[False, False]).groupby('position').head(limit)
    df.position = pd.Categorical(df.position, categories= ['FWD', 'MID', 'DEF', 'GKP'], ordered=True)
    df = df.sort_values(['position', 'past_3_games_avg'], ascending=[True, False])
    return df.to_json(orient='records')

## ENDPOINT: MOST RECENT TRANSFER INS: WISEDOM OF THE CROWDS
@app.route('/topplayers/popular', methods = ['GET'])
def get_popular_players():
    conn = get_db_connection()
    limit = int(request.args.get('limit', 3)) ## defaults to 3 players per pos
    query = f'''
    WITH RecentWeek AS (
    SELECT sp.position, 
            sp.first_name || ' ' || sp.second_name as name,
            st.team_name as team,
            (ph.transfers_in - ph.transfers_out)/100000 AS net_transfers,
            ph.selected/100000 as selected,
            sp.now_cost/10 AS cost_mil,
            sp.total_points AS total_points,
            ROUND(sp.total_points / (sp.now_cost/10), 3) AS value
        FROM PlayerHistories ph
        LEFT JOIN StaticPlayers sp ON ph.element = sp.player_id
        LEFT JOIN StaticTeams st ON sp.team = st.team_id
        WHERE ph.round = (SELECT MAX(round) FROM PlayerHistories)  -- Most recent round
        ORDER BY net_transfers DESC),
    RankedPlayers AS (
    SELECT RecentWeek.*, 
        RANK() OVER (PARTITION BY position ORDER BY selected DESC) as selected_rank, 
        RANK() OVER (PARTITION BY position ORDER BY net_transfers DESC) as net_transfers_rank
    FROM RecentWeek
    )
    SELECT * FROM RankedPlayers 
    WHERE net_transfers_rank <= {limit}
    ORDER BY position, net_transfers DESC
     

    
        
    '''
    df = pd.read_sql(query, conn)
    df = df.sort_values(['position', 'net_transfers'], ascending=[False, False]).groupby('position').head(limit)
    df.position = pd.Categorical(df.position, categories= ['FWD', 'MID', 'DEF', 'GKP'], ordered=True)
    df = df.sort_values(['position', 'net_transfers'], ascending=[True, False])
    conn.close()
    return df.to_json(orient = 'records')


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
    LIMIT 20
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
    df = df.sort_values('round', ascending= True)
    conn.close()
    return df.to_json(orient='records')
    

## Endpoint3: Plot player history 
@app.route('/')
def home():
    return render_template('index.html') ##returns the html on home page 

## RUN THE APP
if __name__ == '__main__':
    app.run(debug=True)