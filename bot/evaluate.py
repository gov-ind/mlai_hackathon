import time
import math
import argparse
import os
import random
import pandas as pd
from datetime import datetime
import numpy as np
import tqdm
import json

from policies import policy_classes
from environment import BatteryEnv, PRICE_KEY, TIMESTAMP_KEY
from plotting import plot_results


def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)['policy']

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)

def run_down_battery(battery_environment: BatteryEnv, market_prices):
    last_day_prices = market_prices[-288:]
    assumed_rundown_price = np.mean(last_day_prices)
    rundown_profits = []
    
    while battery_environment.battery.state_of_charge_kWh > 0:
        energy_removed = battery_environment.battery.discharge_kW(battery_environment.battery.max_discharge_rate_kW)
        rundown_profits.append(battery_environment.get_profit(energy_removed, assumed_rundown_price))

    return rundown_profits

def run_trial(battery_environment, policy):
    profits, socs, market_prices, actions, timestamps = [], [], [], [], []

    state, info = battery_environment.initial_state()
    while True:
        action = policy.act(state, info)

        profits.append(info['total_profit'])
        socs.append(info['battery_soc'])
        market_prices.append(state[PRICE_KEY])
        timestamps.append(state[TIMESTAMP_KEY])
        actions.append(action)

        state, info = battery_environment.step(action)

        if state is None:
            break

    rundown_profits = run_down_battery(battery_environment, market_prices)

    return {
        'profits': profits,
        'socs': socs,
        'market_prices': market_prices,
        'actions': actions,
        'final_soc': socs[-1],
        'rundown_profits': rundown_profits,
        'timestamps': timestamps
    }

def parse_parameters(params_list):
    params = {}
    for item in params_list:
        key, value = item.split('=')
        params[key] = eval(value)
    return params

def perform_eval(args):
    start = time.time()

    if args.class_name:
        policy_config = {'class_name': args.class_name, 'parameters': parse_parameters(args.param)}
    else:
        policy_config = load_config('bot/config.json')

    policy_class = policy_classes[policy_config['class_name']]
    
    external_states = pd.read_csv(args.data)
    if args.output_file:
        output_file = args.output_file
    else:
        results_dir = 'bot/results'
        os.makedirs(results_dir, exist_ok=True)
        output_file = os.path.join(results_dir, f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_{policy_config["class_name"]}.json')

    set_seed(args.seed)

    total_profits = []
    total_rundown_profits = []
    all_trials = []
    start_steps = [args.present_index]
    episode_lengths = [len(external_states) - args.present_index]

    for trial in tqdm.tqdm(range(args.trials - 1)):
        set_seed(args.seed + trial)

        start_step = random.randint(args.present_index, len(external_states) - 1)
        
        episode_length = random.randint(1, len(external_states) - start_step)
        episode_lengths.append(episode_length)
        start_steps.append(start_step)
    
    for start_step, episode_length in zip(start_steps, episode_lengths):
        historical_data = external_states.iloc[:start_step]
        future_data = external_states.iloc[start_step:start_step + episode_length]

        battery_environment = BatteryEnv(data=future_data)

        policy = policy_class(**policy_config.get('parameters', {}))
        policy.load_historical(historical_data)

        trial_data = run_trial(battery_environment, policy)

        total_profits.extend(trial_data['profits'])
        total_rundown_profits.extend(trial_data['rundown_profits'])

        _trial_data = trial_data.copy()
        _trial_data['start_step'] = start_step
        _trial_data['episode_length'] = episode_length

        all_trials.append(_trial_data)

    mean_profit = float(np.mean(total_profits))
    std_profit = float(np.std(total_profits))

    profits_inc_rundown = total_profits + total_rundown_profits
    mean_combined_profit = float(np.mean(profits_inc_rundown))

    outcome = {
        'class_name': policy_config['class_name'],
        'parameters': policy_config.get('parameters', {}),
        'mean_profit': mean_profit,
        'std_profit': std_profit,
        'num_runs': args.trials,
        'score': mean_combined_profit,
        'trials': all_trials,
        'main_trial_idx': 0,
        'seconds_elapsed': time.time() - start 
    }

    print(f'Average profit ($): {mean_profit:.2f} ± {std_profit:.2f}')
    print(f'Average profit inc rundown ($): {mean_combined_profit:.2f}')

    with open(output_file, 'w') as file:
        json.dump(outcome, file, indent=2)

    if args.plot:
        main_trial = outcome['trials'][outcome['main_trial_idx']]
        plot_results(main_trial['profits'], main_trial['market_prices'], main_trial['socs'], main_trial['actions'])

def main():
    parser = argparse.ArgumentParser(description='Evaluate a single energy market strategy.')
    parser.add_argument('--plot', action='store_true', help='Plot the results of the main trial.', default=False)
    parser.add_argument('--present_index', type=int, default=0, help='Index to split the historical data from the data which will be used for the evaluation.')
    parser.add_argument('--trials', type=int, default=1, help='Number of trials to run')
    parser.add_argument('--seed', type=int, default=42, help='Seed for randomness')
    parser.add_argument('--data', type=str, default='bot/data/april15-may7_2023.csv', help='Path to the market data csv file')
    parser.add_argument('--class_name', type=str, help='Policy class name. If not provided, the config.json policy will be used.')
    parser.add_argument('--output_file', type=str, help='File to save all the submission outputs to.', default=None)
    parser.add_argument('--param', action='append', help='Policy parameters as key=value pairs', default=[])
    
    args = parser.parse_args()

    perform_eval(args)

if __name__ == '__main__':
    main()