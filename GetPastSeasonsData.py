## Past seasons
import pandas as pd
import requests
import os
import time
from random_user_agent.user_agent import UserAgent # type: ignore

ua = UserAgent()

## Download and save csv
def downloadnsavecsv(url, filename):

    # File path
    directory = './PastSeasonsData'
    file_name = os.path.join(directory, filename)

    # Create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Download the file
    randomua = ua.get_random_user_agent()
    headers = {'User-Agent': randomua}
    response = requests.get(url, headers= headers)

    if response.status_code == 200:
        # Write content to the file
        with open(file_name, 'wb') as f:
            f.write(response.content)
        print(f"File downloaded successfully as {file_name}")
    else:
        print(f"Failed to download file. HTTP status code: {response.status_code}")


## Download for 2024 and 2023
filesToDownload = ['cleaned_players.csv', 'fixtures.csv', 'teams.csv']
years = ['2022-23', '2023-24']

## URL Format: 
url = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"

## DOWNLOAD RELEVANT DATA
for year in years:
    for file in filesToDownload:
        print(year)
        print(file)
        targeturl = f'{url}/{year}/{file}'
        print(f'downloading : {targeturl}.................')
        target_filename = f'{year.replace("-", "")}_{file}'

        downloadnsavecsv(targeturl, target_filename)

        ## pause
        time.sleep(3)
    time.sleep(2)
