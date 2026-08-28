# import 
import pandas as pd
from pathlib import Path

# getting file path to raw data
root_path = Path(__file__).resolve().parents[1]
file_path = 'data/raw/02aJourneyDataExtract07Fe16-20Feb2016.csv'

# calling first 1000 rows of data
df = pd.read_csv(root_path / file_path, nrows=1000)
print('Dataframe shape', df.shape)
print('Column names as Python list', list(df.columns))

# saving 1000 rows of data as a sample file
output_path = 'data/raw/santander_journeys_sample.csv'
df.to_csv(root_path / output_path, index = False)
print(output_path)