import json
import os
from evaluate import perform_eval, run_down_battery
from environment import BatteryEnv
import argparse

def test_evaluate():
    args = argparse.Namespace()
    args.class_name = 'SimplePolicy'
    args.trials = 1
    args.seed = 42
    args.data = 'bot/data/april15-may7_2023.csv'
    args.output_file = 'bot/results/tmp.json'
    args.param = []
    args.plot = False
    args.present_index = 0

    perform_eval(args)

    assert os.path.exists('bot/results/tmp.json') == True

    with open('bot/results/tmp.json', 'r') as file:
        data = json.load(file)

    assert len(data['trials']) == 1
    main_trial = data['trials'][data['main_trial_idx']]
    assert main_trial['start_step'] == 0
    assert main_trial['episode_length'] == 6335
    assert len(main_trial['profits']) == 6335

    os.remove('bot/results/tmp.json')

def test_evaluate_start_step():
    args = argparse.Namespace()
    args.class_name = 'SimplePolicy'
    args.trials = 1
    args.seed = 42
    args.data = 'bot/data/april15-may7_2023.csv'
    args.output_file = 'bot/results/tmp.json'
    args.param = []
    args.plot = False
    args.present_index = 100

    perform_eval(args)

    assert os.path.exists('bot/results/tmp.json') == True

    with open('bot/results/tmp.json', 'r') as file:
        data = json.load(file)

    assert len(data['trials']) == 1
    main_trial = data['trials'][data['main_trial_idx']]
    assert main_trial['start_step'] == 100
    assert main_trial['episode_length'] == 6235
    assert len(main_trial['profits']) == 6235
    assert len(main_trial['actions']) == 6235

    os.remove('bot/results/tmp.json')

def test_rundown_battery():
    battery_environment = BatteryEnv(data='bot/train.csv', initial_charge=305, discharge_rate_kW=20, efficiency=1.0)
    market_prices = [10, 10, 10, 10, 10]
    profits = run_down_battery(battery_environment, market_prices)

    assert battery_environment.battery.state_of_charge_kWh == 0