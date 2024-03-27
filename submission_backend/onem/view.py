from matplotlib import pyplot as plt
import datetime
import pandas as pd

df = pd.read_parquet('submission_backend/cruft/price_and_demand_data.parquet')
df = df.rename(columns={'timezone': 'timestamp'})
       
# show where all the nans are in the data on a plot vs time

df['price_is_nan'] = df['price'].isna()

# plt.plot(df['timestamp'], df['price_is_nan'])
# plt.show()

# show the first date on which there was a NAN
print(df[df['price_is_nan'] == True].head(1))

# there are long sunning segments of price nans, print out each time a consecutive segment of nans starts or stops
nan_segments = []
nan_segment = []
for i, row in df.iterrows():
    if row['price_is_nan']:
        nan_segment.append(row['timestamp'])
    else:
        if len(nan_segment) > 0:
            nan_segments.append(nan_segment)
            nan_segment = []

for segment in nan_segments:
    print(segment[0], segment[-1])