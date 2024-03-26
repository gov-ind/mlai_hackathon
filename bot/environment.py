"""
This file contains the core functionality for the battery simulation environment and its interaction with the NEM.
It provides a realistic representation of the NEM's operations and the battery's role within it.
Contestants will use this environment to develop and test their bidding strategies.

Units used in this file:
- Power: kilowatts (kW)
- Energy: kilowatt-hours (kWh)
- Time: minutes (min)
- Price: dollars per kilowatt-hour ($/kWh)
"""

import pandas as pd
import numpy as np
from collections import deque
from typing import Tuple

INTERVAL_DURATION = 5  # Duration of each dispatch interval in minutes
PRICE_KEY = 'price'
TIMESTAMP_KEY = 'timestamp'

class Battery:
    """
    A simple model of a battery with charging and discharging capabilities.
    """
    def __init__(self, capacity: float, charge_rate: float, discharge_rate: float, 
                 initial_charge: float, efficiency: float = 0.9):
        """
        Initialize the battery with the given parameters.

        :param capacity: Maximum energy capacity of the battery in kWh.
        :param charge_rate: Maximum charging rate in kW.
        :param discharge_rate: Maximum discharging rate in kW.
        :param initial_charge: Initial state of charge of the battery in kWh.
        :param efficiency: Charging and discharging efficiency of the battery (default: 0.9).
        """
        self.capacity_kWh = capacity
        self.initial_charge_kWh = initial_charge
        self.max_charge_rate_kW = charge_rate
        self.max_discharge_rate_kW = discharge_rate
        self.efficiency = efficiency
        self._state_of_charge_kWh = min(self.initial_charge_kWh, self.capacity_kWh)

    def reset(self):
        """Reset the battery to its initial state of charge."""
        self._state_of_charge_kWh = min(self.initial_charge_kWh, self.capacity_kWh)

    def charge_kW(self, kW: float) -> float:
        """
        Charge the battery with a specified power over a duration.

        :param power: Power in kW to charge the battery.
        :param duration: Duration in minutes for which the battery is charged.
        :return: Energy added to the battery in kWh.
        """
        kW = min(kW, self.max_charge_rate_kW)
        energy_add_order = kW * (INTERVAL_DURATION / 60) * self.efficiency  # Convert power (kW) to energy (kWh)
        energy_added = min(energy_add_order, self.capacity_kWh - self._state_of_charge_kWh)
        self._state_of_charge_kWh = min(self._state_of_charge_kWh + energy_add_order, self.capacity_kWh)
        return energy_added

    def discharge_kW(self, kW: float) -> float:
        """
        Discharge the battery with a specified power over a duration.

        :param power: Power in kW to discharge the battery.
        :param duration: Duration in minutes for which the battery is discharged.
        :return: Energy removed from the battery in kWh.
        """
        kW = min(kW, self.max_discharge_rate_kW)
        energy_remove_order = kW * (INTERVAL_DURATION / 60) / self.efficiency  # Convert power (kW) to energy (kWh)
        energy_removed = min(energy_remove_order, self._state_of_charge_kWh)
        self._state_of_charge_kWh = max(self._state_of_charge_kWh - energy_remove_order, 0)
        return energy_removed

    @property
    def state_of_charge_kWh(self) -> float:
        return self._state_of_charge_kWh


class BatteryEnv:
    """
    Environment for simulating battery operation in the National Electricity Market (NEM) context.
    """
    def __init__(self, data, capacity_kWh: float = 13, charge_rate_kW: float = 5, discharge_rate_kW: float = 5,
                 initial_charge: float = 7.5, efficiency: float = 0.9):
        """
        Initialize the battery environment with the given parameters.

        :param capacity: Maximum energy capacity of the battery in kWh (default: 100).
        :param charge_rate: Maximum charging rate in kW (default: 50).
        :param discharge_rate: Maximum discharging rate in kW (default: 50).
        :param initial_charge: Initial state of charge of the battery in kWh (default: 50).
        :param data: Path to the CSV file containing market data (default: 'train.csv').
        """
        self.battery = Battery(capacity_kWh, charge_rate_kW, discharge_rate_kW, initial_charge, efficiency=efficiency)
        self.market_data = data
        self.total_profit = 0
        self.current_step = 0
        self.episode_length = len(self.market_data)

    def initial_state(self):
        assert self.current_step == 0

        return self.market_data.iloc[self.current_step], self.get_info(0)

    def step(self, quantity: float) -> Tuple[pd.Series, dict]:
        """
        Perform a single step in the environment based on the given action.

        :param action: A tuple containing the bid price ($/kWh) and quantity (kW) for the current step.
        :return: A tuple containing the next market data and information dictionary, or (None, None) if the episode is done.
        """
        if self.current_step >= len(self.market_data) - 1:
            return None, None
        market_price = self.market_data.iloc[self.current_step][PRICE_KEY]
        profit_delta = self.process_action(quantity, market_price)
        self.current_step += 1
        market_data = self.market_data.iloc[self.current_step]
        return market_data, self.get_info(profit_delta)
    
    def get_profit(self, energy_removed: float, spot_price_mWh: float) -> float:
        return round(energy_removed * spot_price_mWh / 1000, 2) # Convert energy (kWh) to revenue ($)

    def process_action(self, quantity: float, spot_price: float) -> float:
        """
        Process the action taken by the agent and return the profit delta.

        :param action: A tuple containing the bid price ($/kWh) and quantity (kW) for the current step.
        :param spot_price: The current spot price in $/kWh.
        :return: The profit delta in dollars.
        """
        if quantity > 0:
            energy_added = self.battery.charge_kW(quantity)
            return -self.get_profit(energy_added, spot_price) 
        elif quantity < 0:
            energy_removed = self.battery.discharge_kW(-quantity)
            return self.get_profit(energy_removed, spot_price)
        return 0

    def get_info(self, profit_delta: float = 0) -> dict:
        """
        Return a dictionary containing relevant information for the agent.

        :param profit_delta: The change in profit from the last action (default: 0).
        :return: A dictionary containing information about the current state of the environment.
        """
        self.total_profit += profit_delta
        remaining_steps = len(self.market_data) - self.current_step - 1
        return {
            'total_profit': self.total_profit,
            'profit_delta': profit_delta,
            'battery_soc': self.battery.state_of_charge_kWh,
            'max_charge_rate': self.battery.max_charge_rate_kW,
            'max_discharge_rate': self.battery.max_discharge_rate_kW,
            'remaining_steps': remaining_steps
        }