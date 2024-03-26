import polars as pl
import datetime

# Read the data
df = pl.read_parquet('submission_backend/cruft/price_and_demand_data.parquet')

# # Rename 'timezone' column to 'timestamp' and remove 'forecast_load' column
# df = df.rename({"timezone": "timestamp"}).drop("forecast_load")

# # Remove all data before 2021-09-30 23:55:00
# df = df.filter(df["timestamp"] > datetime.datetime(2021, 9, 30, 23, 55))

# # Interpolate all NaN prices so that they are the same price as the price at the next timestamp
# # Note: Polars' fill_none() function with 'backward' method achieves a similar backfill operation.
# # However, direct row-wise comparisons or operations might require different approaches in Polars.
# df = df.with_column(
#     pl.col("price").fill_none("backward")
# )

# Count NaNs
# In Polars, we use `is_null()` and then sum each column to count NaNs.
# This operation returns a DataFrame with the sum of null values per column.
nan_counts = df.select([pl.col(column).is_null().sum().alias(f"{column}_nan_count") for column in df.columns])
print(nan_counts)
