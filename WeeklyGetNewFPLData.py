## Script that runs every week 
## Builds on the original file that first ran the webscrape and first created the sql tables 

import requests
import pandas as pd
from sqlite3 import connect
import time 
from tqdm.auto import tqdm


#########################################################
## get teams and positions static data 
url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
response = requests.get(url)
data = response.json() ## extracting the response in JSON format 

#########################################################


## Constants
base_url = 'https://fantasy.premierleague.com/api/'
db_name = 'fpl_data.db'

## Get DB connection 
def db_connect(db_name = db_name):
    '''connect to sqlite database'''
    conn = connect(db_name)
    conn.row_factory = lambda cursor, row: {cursor.description[idx][0]: value for idx, value in enumerate(row)} ## set rows to be dictionaries for easier indexingb 
    return conn


###################################
## 1. FETCH STATIC DATA (PLAYERS, TEAMS)
def fetch_static_data():
    response = requests.get(base_url+'bootstrap-static/')
    return response.json()

def get_player_history(pid):
    response = requests.get(base_url+f'element-summary/{pid}/')
    return response.json()


def update_static_data(static_data):
    '''simply replace the static player and static teams data with the updated one'''
    conn = db_connect()
    if static_data:
        players = pd.DataFrame(static_data['elements'])
        positions = pd.DataFrame(static_data['element_types'])
        teams = pd.DataFrame(static_data['teams'])
        fixtures = pd.DataFrame(static_data['events'])

        #1. teams
        str_cols = [col for col in teams.columns if 'strength' in col]
        teams = teams[str_cols + ['name'] + ['id']]
        teams.rename(columns = {'name':'team_name', 'id': 'team_id'}, inplace = True)
        teams.to_sql('StaticTeams', conn, if_exists='replace', ## not append -- will create duplicates  
                     index=False)

        ## clean and insert the data into sql database
        players_with_teams = pd.merge(left = players, right = teams, 
        left_on = 'team',
        right_on = 'team_id')
        players_with_teams_positions =  pd.merge(left = players_with_teams, right = positions[['id', 'plural_name_short']], 
        left_on = 'element_type', ## representing player position
        right_on = 'id') 
        players_with_teams_positions.drop(columns=['id_y'], inplace=True)
        players_with_teams_positions.rename(columns={'id_x':'player_id'}, inplace=True)
        players_with_teams_positions.rename(columns={'plural_name_short':'position'}, inplace=True)


        
        #2. players
        players_cols = ['player_id', 'first_name', 'second_name', 'team', 'total_points', 'now_cost', 
                        'influence', 'creativity', 'threat', 'points_per_game', 'position']
        players = players_with_teams_positions[players_cols]
        players.rename(columns={'id': 'player_id'}, inplace=True)
        players.to_sql('StaticPlayers', conn, if_exists='replace', index=False)


        #3. fixtures 
        fixtures['deadline_time'] = pd.to_datetime(fixtures['deadline_time'])
        fixtures['deadline_date'] = fixtures['deadline_time'].dt.date
        fixtures['deadline_time'] = fixtures['deadline_time'].dt.time
        fixtures_col = ['id', 'name', 'average_entry_score','deadline_date','deadline_time', 'most_captained', 'most_vice_captained']
        fixtures[fixtures_col].to_sql(name='Fixtures', con=conn, if_exists='replace', index=False)

        

        ## done!
        conn.commit() ## make sure to run the code
        conn.close() ## done
        print('Database updated')
    else:
        print('No data to upload to sql')


## 2. GET PLAYER HISTORIES (MORE TIME CONSUMING)
def update_player_histories():
    players_table_cols = ['player_id', 'now_cost', 'points_per_game', 'first_name', 'second_name', 'team', 'total_points', 
                      'transfers_in', 'transfers_out', 'selected_by_percent', 'goals_scored', 'assists', 
                      'clean_sheets', 'goals_conceded', 'yellow_cards', 'red_cards', 'bonus', 'influence', 'creativity',
                        'threat', 'expected_goals_per_90', 'expected_assists_per_90', 'position']

    ## retrieve the player ids 
    conn = db_connect()
    curr = conn.cursor()

    ## Get previous max round 
    last_round  = curr.execute('select max(round) from PlayerHistories').fetchone()['max(round)']

    ## Get player ids 
    player_ids = curr.execute('select player_id from StaticPlayers where total_points > 0') ## get list of dictionaries (one for each row)
    player_ids = [row['player_id'] for row in player_ids] ## extract into a single level list

    ## Get player histories (time consuming)
    ## Create a new_histories list to append to db at the end
    new_histories_all = [] ## collects one new round per player (if run weekly)

    for pid in tqdm(player_ids, desc = 'Fetching player histories'):
        player_hist = get_player_history(pid)['history'] ##other options: fixtures
        ## filter for new info
        for game in player_hist: 
            if game['round'] > last_round:
                new_histories_all.append(game)
    
    if new_histories_all:
        new_histories_df = pd.DataFrame(new_histories_all)
        new_histories_df.kickoff_time = pd.to_datetime(new_histories_df.kickoff_time)
        new_histories_df['kickoff_date'] = new_histories_df.kickoff_time.dt.date
        new_histories_df['kickoff_time'] = new_histories_df.kickoff_time.dt.time
        new_histories_df = new_histories_df.drop(columns=['kickoff_time'])
        existing_cols_query = "PRAGMA table_info(PlayerHistories)"
        existing_cols = [row['name'] for row in conn.execute(existing_cols_query).fetchall()]
        new_histories_df = new_histories_df[[col for col in new_histories_df.columns if col in existing_cols]]


        new_histories_df.to_sql('PlayerHistories', conn, 
                                if_exists='append', index=False)
        print(f'Inserted {len(new_histories_df)} new rows into PlayerHistories.')
    else:
        print('No new round data to add for playerhistories')
    
    conn.commit()
    conn.close()
        
    
    

## FINAL FUNCTION #####
def run_weekly_update():
    print('Fetching static data from FPL api')
    static_data = fetch_static_data()
    print('--- done fetching static data')

    print('Updating the database for static data')
    update_static_data(static_data)

    print('Updating player histories')
    update_player_histories()

    ## Done
    print('DONE! -----------')



## RUN WEEKLY 
if __name__ == '__main__':
    run_weekly_update()

    ## Check
    db_name = 'fpl_data.db'
    conn = db_connect(db_name=db_name)
    curr = conn.cursor()
    curr.execute('select max(round) from PlayerHistories')
    print(curr.fetchall())
    conn.close()