import pandas as pd
from math import inf

TIMESTAMP_COL = 'timestamp'

class EnergyDB():
    '''
    A simple in-memory DB backed by a CSV. WARNING: No locks used and not thread-safe.
    '''
    def __init__(self, file_location: str='bot/data/april15-may7_2023.csv', timestamp_col: str=TIMESTAMP_COL):
        self.file_location = file_location
        self.timestamp_col = timestamp_col
        self.__load_data()

    def __load_data(self):
        self.data = pd.read_csv(self.file_location, parse_dates=[self.timestamp_col])
        self.data[self.timestamp_col] = self.data[self.timestamp_col].apply(lambda x: int(x.timestamp()))

    def get_data(self, unix_start: int=0, unix_end: int=inf):
        assert unix_start < unix_end
        timeslice = self.data[(self.data[self.timestamp_col] >= unix_start) & (self.data[self.timestamp_col] < unix_end)]
        return timeslice

    def save_new_data(self, data: pd.DataFrame) -> int:
        latest_known_time = self.latest_timestamp()
        if pd.isna(latest_known_time):
            latest_known_time = 0

        # Convert to Unix timestamp first, filter, and then convert back to datetime
        if data[self.timestamp_col].dtype != float:
            timezone = data[self.timestamp_col].dt.tz
            if timezone is not None:
                tzname = timezone.tzname(None)
            else:
                tzname = None
            data[self.timestamp_col] = data[self.timestamp_col].apply(lambda x: x.timestamp())
        data_to_add = data[data[self.timestamp_col] > latest_known_time]
        if data_to_add[self.timestamp_col].dtype == float:
            datetimes = pd.to_datetime(
                data_to_add[self.timestamp_col], unit='s', utc=True
            )
            if tzname is not None:
                datetimes = datetimes.dt.tz_convert(tzname)
            data_to_add[self.timestamp_col] = datetimes

        if not data_to_add.empty:
            data_to_add.to_csv(self.file_location, mode='a', header=False, index=False)
            self.__load_data()
        return data_to_add.shape[0]

    def latest_timestamp(self):
        if self.data.empty:
            return float('nan')
        last_row = self.data.tail(1)
        return int(last_row[self.timestamp_col].values[0])

    def earliest_timestamp(self):
        if self.data.empty:
            return float('nan')
        first_row = self.data.head(1)
        return int(first_row[self.timestamp_col].values[0])
