## Getting the data
import requests 
import pandas as pd
import time

## Get season data
url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
response = requests.get(url)
data = response.json() ## extracting the response in JSON format 

## Sorting out the different data
from pprint import pprint
pprint(data, indent = 2, depth = 1, compact=True)

## 1, Player data
players = pd.DataFrame(data['elements'])
teams = pd.DataFrame(data['teams'])
fixtures = pd.DataFrame(data['events'])
positions = pd.DataFrame(data['element_types'])

## Save as csvs
# players.to_csv('Players.csv')
# teams.to_csv('Teams.csv')
# fixtures.to_csv('Fixtures.csv')
# positions.to_csv('Positions.csv')

## Read csvs
players = pd.read_csv('CurrentSeasonData/Players.csv', index_col=0)
teams = pd.read_csv('CurrentSeasonData/Teams.csv', index_col=0)
fixtures = pd.read_csv('CurrentSeasonData/Fixtures.csv', index_col=0)
positions = pd.read_csv('CurrentSeasonData/Positions.csv', index_col=0)


## Exploring the data 
fixtures.head()
fixtures.columns

players.head()
########################################################################################
## Basic cleaning 

## remove players who dont play 
(players.total_points < 10).value_counts()
players = players[players.total_points > 10].reset_index(drop=True)

## Select only useful cols 
## Teams 
str_cols = [col for col in teams.columns if 'strength' in col]
teams = teams[str_cols + ['name'] + ['id']]
teams.rename(columns = {'name':'team_name', 'id': 'team_id'}, inplace = True)
## Merging in team and position information 
players_with_teams = pd.merge(left = players, right = teams, 
        left_on = 'team',
        right_on = 'team_id')
players_with_teams_positions =  pd.merge(left = players_with_teams, right = positions[['id', 'plural_name_short']], 
        left_on = 'element_type', ## representing player position
        right_on = 'id') 
players_with_teams_positions.drop(columns=['id_y'], inplace=True)
players_with_teams_positions.rename(columns={'id_x':'player_id'}, inplace=True)
players_with_teams_positions.rename(columns={'plural_name_short':'position'}, inplace=True)

## SAVE THIS NEW STATIC PLAYERS TABLE -- WITH TEAMS AND POSITIONS DATA
players_with_teams_positions.to_csv('./CurrentSeasonData/Players_with_teams_positions.csv')

########################################################################################
## MERGE CURRENT AND PAST DATA! 

## Need to first get player histories for this season 
base_url = 'https://fantasy.premierleague.com/api/'

## Create a function that produces an entire history dataframe for a particular player
## given his player ID (PID)
def get_player_history(pid):
    player_hist_json = requests.get(
        base_url + 'element-summary/' + str(pid) + '/' ).json()
    player_hist_df = pd.json_normalize(player_hist_json['history']) ## use 'history' to get player current season history 
    time.sleep(1)
    return(player_hist_df)

## Load each player history -- takes a while, can reduce sleep time if needs to be faster
# from tqdm.auto import tqdm
# tqdm.pandas()
# players_histories = players.id.progress_apply(get_player_history)

## Check
# full_history_df = pd.concat(history for history in players_histories) ## use list comprehension

# ## Save csv
# full_history_df.to_csv('CurrentSeasonData/PlayerHistories.csv')

## Merge in histories to player data 
merged_df = pd.merge(players_with_teams_positions, full_history_df, how='inner', 
                     left_on='player_id', 
                     right_on='element')

## Remove same cols (cols that end with _x)
x_cols = [col for col in merged_df.columns if '_x' in col]
merged_df = merged_df.drop(columns=x_cols)
y_cols = [col for col in merged_df.columns if '_y' in col]
y_cols_cleaned = [col.replace('_y', '') for col in y_cols]

merged_df = merged_df.rename(columns=dict(zip(y_cols, y_cols_cleaned)))

## we finally have game by game data from players, including statis data such as team, total points, current trfs balance, etc 
merged_df.to_csv('./CurrentSeasonData/CurrentSeasonHistoriesMerged.csv')

## IMPORTANT INFO ONLY 
merged_df.columns.tolist()


###################################################################################
###################################################################################
## SET UP THE DATABASE
from sqlite3 import connect

## Create the db and connect to it 
conn = connect('fpl_data.db')
curr = conn.cursor()

## CREATE STATIC PLAYERS TABLE ------------------------------------------
players_table_cols = ['player_id', 'now_cost', 'points_per_game', 'first_name', 'second_name', 'team', 'total_points', 
                      'transfers_in', 'transfers_out', 'selected_by_percent', 'goals_scored', 'assists', 
                      'clean_sheets', 'goals_conceded', 'yellow_cards', 'red_cards', 'bonus', 'influence', 'creativity',
                        'threat', 'expected_goals_per_90', 'expected_assists_per_90', 'position']
curr.execute('''
CREATE TABLE IF NOT EXISTS StaticPlayers(
            player_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            now_cost REAL, 
            points_per_game REAL, 
            first_name TEXT, 
            second_name TEXT, 
            team TEXT, 
            total_points INTEGER, 
            transfers_in INTEGER,
            transfers_out INTEGER,
            selected_by_percent REAL,
            goals_scored INTEGER,
            assists INTEGER,
            clean_sheets INTEGER,
            goals_conceded INTEGER,
            yellow_cards INTEGER,
            red_cards INTEGER,
            bonus INTEGER,
            influence REAL,
            creativity REAL,
            threat REAL,
            expected_goals_per_90 REAL,
            expected_assists_per_90 REAL,
            position TEXT)
''')


## CREATE PLAYER HISTORIES TABLE ------------------------------------------------

## Some precleaning 
full_history_df.kickoff_time = pd.to_datetime(full_history_df.kickoff_time)
full_history_df['kickoff_date'] = full_history_df.kickoff_time.dt.date
full_history_df['kickoff_time'] = full_history_df.kickoff_time.dt.time

curr.execute('''
CREATE TABLE IF NOT EXISTS PlayerHistories (
    player_id INTEGER PRIMARY KEY AUTOINCREMENT,
    element INTEGER,
    fixture INTEGER,
    opponent_team INTEGER,
    total_points INTEGER,
    was_home INTEGER,
    kickoff_date DATE,
    team_h_score INTEGER,
    team_a_score INTEGER,
    round INTEGER,
    modified TEXT,
    minutes INTEGER,
    goals_scored INTEGER,
    assists INTEGER,
    clean_sheets INTEGER,
    goals_conceded INTEGER,
    own_goals INTEGER,
    penalties_saved INTEGER,
    penalties_missed INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,
    saves INTEGER,
    bonus INTEGER,
    bps INTEGER,
    influence REAL,
    creativity REAL,
    threat REAL,
    ict_index REAL,
    starts INTEGER,
    expected_goals REAL,
    expected_assists REAL,
    expected_goal_involvements REAL,
    expected_goals_conceded REAL,
    value REAL,
    transfers_balance INTEGER,
    selected INTEGER,
    transfers_in INTEGER,
    transfers_out INTEGER
)
''')


## POPULATE THE DATABASE TABLES 

## Populate first table
players_with_teams_positions[players_table_cols].to_sql('StaticPlayers', 
                                                        conn, if_exists='append', 
                                                        index=False)

## Populate second table 

full_history_df.drop(columns=['kickoff_time']).to_sql('PlayerHistories', conn, if_exists='append', index=False)


## Check that sql tables are filled correctly
pd.read_sql('SELECT first_name, second_name, total_points FROM StaticPlayers WHERE points_per_game > 4 LIMIT 5', conn)


## CREATE FIXTURES TABLE ------------------------------------------------
today = pd.Timestamp.today()
fixtures[fixtures.average_entry_score == 0].name.head(1)
## Clean
fixtures['deadline_time'] = pd.to_datetime(fixtures['deadline_time'])
fixtures['deadline_date'] = fixtures['deadline_time'].dt.date
fixtures['deadline_time'] = fixtures['deadline_time'].dt.time


fixtures_col = ['id', 'name', 'average_entry_score','deadline_date','deadline_time', 'most_captained', 'most_vice_captained']

##

curr.execute('''
CREATE TABLE IF NOT EXISTS Fixtures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name text, 
    average_entry_score INT, 
    deadline_date DATE, 
    deadline_time TIME, 
    most_captained INT, 
    most_vice_captained INT 
)
''')
conn.commit()

## populate the table via pd 
fixtures[fixtures_col].to_sql(name='Fixtures', con=conn, if_exists='append', index=False)


## TESTING -- DELETE LATER
pd.read_sql('SELECT name as gameweek, deadline_date, deadline_time from fixtures where average_entry_score == 0 ORDER BY deadline_date LIMIT 1', conn)
query = 'SELECT first_name, second_name, team, now_cost, total_points, position FROM StaticPlayers ORDER BY total_points DESC LIMIT 5'
pd.read_sql(query, conn)