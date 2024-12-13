import pandas as pd

## 1. Download the csvs from the github
past_merged_gw = 'https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/refs/heads/master/data/2023-24/gws/merged_gw.csv'
past_teams  = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/refs/heads/master/data/{}/teams.csv"

# Load past seasons' data
merged_gw_2023 = pd.read_csv(past_merged_gw.format('2023-24'))
merged_gw_2023['seasonEnd'] = 2024

teams_2023 = pd.read_csv(past_teams.format('2023-24'))
teams_2023['seasonEnd'] = 2024

merged_gw_2022 = pd.read_csv(past_merged_gw.format('2022-23'))
merged_gw_2022['seasonEnd'] = 2023
teams_2022 = pd.read_csv(past_teams.format('2022-23'))
teams_2022['seasonEnd'] = 2023

# Combine historical gameweek data
merged_gw = pd.concat([merged_gw_2023, merged_gw_2022], ignore_index=True)

## Check
print(f'size of merged gw: {merged_gw.shape}')

# Combine historical teams data
teams = pd.concat([teams_2023, teams_2022], ignore_index=True)

## 2. Merge the gameweek data with the teams data -- incoporate team strs in the gameweek data 
teams.columns
merged_gw.columns
merged_gw[['name', 'team', 'GW', 'opponent_team']]

teams[['code', 'id', 'name']]

## merged_gw['team'] corresponds to teams['name']#
set(merged_gw.team) == set(teams.name)
## merged_gw['opponent_team] corres ponds to teams
set(merged_gw.opponent_team) == set(teams.id)

## Merge based on those columns 
str_cols = [col for col in teams.columns if 'strength' in col] + ['name', 'id', 'seasonEnd']
teams[str_cols]

## 2.1 add the player's team info 
merge_1 = merged_gw.merge(teams[str_cols], 
                left_on=['team', 'seasonEnd'], 
                right_on= ['name', 'seasonEnd'], 
                how = 'left')
## rename for readibility 
merge_1.rename(columns={
    'strength_overall_home': 'team_strength_home',
    'strength_overall_away': 'team_strength_away',
    'strength_attack_home': 'team_attack_home',
    'strength_attack_away': 'team_attack_away',
    'strength_defence_home': 'team_defence_home',
    'strength_defence_away': 'team_defence_away'
}, inplace=True)

## 2.2 add the opponent team info
final_merge = merge_1.merge(teams[str_cols], 
                left_on = ['opponent_team', 'seasonEnd'], 
                right_on = ['id', 'seasonEnd'], 
                how='left')
## rename 
final_merge.rename(columns={
    'strength_overall_home': 'opponent_strength_home',
    'strength_overall_away': 'opponent_strength_away',
    'strength_attack_home': 'opponent_attack_home',
    'strength_attack_away': 'opponent_attack_away',
    'strength_defence_home': 'opponent_defence_home',
    'strength_defence_away': 'opponent_defence_away'
}, inplace=True)

## Remove unnec cols 
final_merge.columns
final_merge.drop(columns= ['name', 'team'], inplace=True) ## remove team names

## Save as CSV 
final_merge.to_csv('./PastSeasonsData/Cleaned2022-2024GWData.csv')

## #################### MODELLING 
## PREDICTORS 
predictors = ['position', 'creativity', 'influence', 'threat', 'transfers_balance', 'was_home', 'opponent_strength_home',
                'opponent_strength_away', 'team_strength_home', 'team_strength_away']
final_merge[predictors]

## 3. FEATURE ENGINEERING 
## 3.1 make sure the data is correctly sorted by date, as we will be taking rolling averages
final_merge['kickoff_time'] = pd.to_datetime(final_merge['kickoff_time'])
final_merge = final_merge.sort_values(by = ['name_x', 'kickoff_time'])

## 3.2 Taking rolling averages of ICT
ICTs = ['creativity', 'influence', 'threat']
for feature in ICTs:
    final_merge[f'{feature}_rolling_avg_2'] = (
        final_merge.groupby('name_x')[feature].rolling(window=2).mean().reset_index(0, drop=True)
    )

##Check if makes sense

## 3.3 One week lag for trf balance?
# final_merge[final_merge.GW ==1][['name_x', 'total_points', 'transfers_balance', 'GW']][final_merge['total_points'] > 0]## check - yes, need to lag by one week 
final_merge['transfers_balance_lag'] = final_merge.groupby('name_x')['transfers_balance'].shift(1)