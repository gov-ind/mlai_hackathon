import pandas as pd
from collections import deque
import numpy as np
from policies.policy import Policy

class MovingAveragePolicy(Policy):
    def __init__(self, window_size=5):
        """
        Constructor for the MovingAveragePolicy.

        :param window_size: The number of past market prices to consider for the moving average (default: 5).
        """
        super().__init__()
        self.window_size = window_size
        self.price_history = deque(maxlen=window_size)

    def act(self, external_state, internal_state):
        market_price = external_state['price']
        self.price_history.append(market_price)

        if len(self.price_history) == self.window_size:
            moving_average = np.mean(self.price_history)
            
            if market_price > moving_average:
                quantity = -internal_state['max_discharge_rate']
            else:
                quantity = internal_state['max_charge_rate']
        else:
            quantity = 0

        return quantity

    def load_historical(self, external_states: pd.DataFrame):   
        for price in external_states['price'].values:
            self.price_history.append(price)