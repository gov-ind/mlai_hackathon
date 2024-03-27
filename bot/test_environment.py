import numpy as np
import pandas as pd
from bot.environment import BatteryEnv, Battery, INTERVAL_DURATION

def test_battery_environment():
    data = pd.read_csv('bot/data/april15-may7_2023.csv')
    battery_env = BatteryEnv(data=data, capacity_kWh=10000, charge_rate_kW=5, discharge_rate_kW=5, initial_charge=7.5)
    state, info = battery_env.initial_state()


    count = 0
    while True:
        quantity = 1

        state, info = battery_env.step(quantity)

        count += 1
        if state is None:
            break
    
    assert count == len(data)
    
    duration_in_hours = INTERVAL_DURATION / 60
    energy_MWh = quantity * battery_env.battery.efficiency * duration_in_hours / 1000
    expected_total_profit = -(
        data["price"] * energy_MWh
    ).round(2).sum()
    assert battery_env.total_profit < 0
    assert np.isclose(battery_env.total_profit, expected_total_profit, atol=1e-2)


def test_price_for_single_discharge():
    data = pd.read_csv('bot/data/april15-may7_2023.csv')
    battery_env = BatteryEnv(data=data, capacity_kWh=10000, charge_rate_kW=5, discharge_rate_kW=5, initial_charge=7.5)

    energy = 5
    spot_price_MWh = 100
    profit = battery_env.get_profit(energy, spot_price_MWh)
    expected_profit = energy * spot_price_MWh / 1000

    assert np.isclose(profit, expected_profit)

def test_battery_charges_once():
    battery = Battery(capacity=13, charge_rate=5, discharge_rate=5, initial_charge=0, efficiency=1.0)
    charge = battery.charge_kW(5)
    assert abs(charge - 0.41666666666666663) < 0.01
    assert abs(battery.state_of_charge_kWh - 0.41666666666666663) < 0.01

    charge = battery.charge_kW(5)
    assert abs(charge - 0.41666666666666663) < 0.01
    assert abs(battery.state_of_charge_kWh - (2* 0.41666666666666663)) < 0.01
