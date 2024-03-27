from matplotlib import pyplot as plt
import datetime
import pandas as pd

df = pd.read_parquet('submission_backend/cruft/price_and_demand_data.parquet')
df = df.rename(columns={'timezone': 'timestamp'})
del df['forecast_load']

# remove all data before 2021-09-30 23:55:00
df = df[df['timestamp'] > datetime.datetime(2021, 9, 30, 23, 55)]

# interpolate all nan prices so that they are the same price as the price
# at the next timestamp such that that price is not a nan
df['price'] = df['price'].fillna(method='bfill')

# count nans
print(df.isna().sum())

end_date = df['timestamp'].max()
six_months_before_end = end_date - datetime.timedelta(days=180)

validation_dataset = df[df['timestamp'] > six_months_before_end]
training_dataset = df[df['timestamp'] <= six_months_before_end]

# validation_dataset.to_csv('bot/data/validation.csv', index=False)
# training_dataset.to_csv('bot/data/training.csv', index=False)

start_april = datetime.datetime(2023, 4, 15)
end_april = datetime.datetime(2023, 5, 7)

april = df[(df['timestamp'] > start_april) & (df['timestamp'] < end_april)]

april.to_csv('bot/data/april15-may7_2023.csv', index=False)

print('timesteps in training dataset', len(training_dataset))
print('timesteps in validation dataset', len(validation_dataset))
print('timesteps in april dataset', len(april))

# end_date = df['timezone'].max()
# set the final six months aside as validation data




# df = pd.read_parquet('submission_backend/cruft/weather_data.parquet')

# print(df.columns)

# print(df.tail())




# df = pd.read_parquet('submission_backend/cruft/generation_data.parquet')

# print(df.columns)

# print(df.tail())