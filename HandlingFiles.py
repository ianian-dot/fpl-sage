import os

if not os.path.exists('CurrentSeasonData'):
    os.mkdir('CurrentSeasonData')
else:
    print('Folder exists')
## Move csvs to the new folder
os.replace('Fixtures.csv', 'CurrentSeasonData/Fixtures.csv')
os.replace('Players.csv', 'CurrentSeasonData/Players.csv')
os.replace('Teams.csv', 'CurrentSeasonData/Teams.csv')