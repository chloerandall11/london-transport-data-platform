from pathlib import Path
import pandas as pd

# getting file path to sample data 
root_path = Path(__file__).resolve().parents[1]
file_path = 'data/raw/santander_journeys_sample.csv'

df = pd.read_csv(root_path / file_path)
df.info()