import src.xxapi as xxapi
import numpy as np
from collections import defaultdict
import requests

def fetch_validator_info():
    url = "https://dashboard-api.xx.network/v1/nodes"
    response = requests.get(url)
    data = response.json()

    # Create a dictionary where the keys are the wallet addresses and the values are the geo bins
    validators_geo_bins = {}
    for node in data["nodes"]:
        if node['status'] == 'online':  # Only consider the node if its status is online
            validators_geo_bins[node['walletAddress']] = node['geoBin']

    return validators_geo_bins

def main():
    # Connect to chain
    xxchain = xxapi.XXNetworkInterface("wss://xx.api.onfinality.io/public-ws")
    if xxchain is None:
        exit(1)

    eras = 10  # Specify the number of eras
    curr_era = xxchain.item_query("Staking", "ActiveEra")['index']
    end_era = curr_era - 1
    start_era = end_era - eras + 1

    validators_geo_bins = fetch_validator_info()

    # Get performance points of validators and group them by geo bins
    geo_bin_points = defaultdict(lambda: defaultdict(int)) # default to 0 for total points for each geo bin for each era

    # Fetch rewards data for all validators across the eras
    rewards_data = xxchain.staking_rewards(validators_geo_bins.keys(), start_era, end_era)

    for validator_data in rewards_data["accounts"]:
        # Get geo bin for the validator
        geo_bin = validators_geo_bins.get(validator_data["address"], None)
        if geo_bin is not None:
            for era, rewards in validator_data["rewards"].items():
                for reward_data in rewards:
                    points = reward_data["reward"]
                    # Add validator's points to the corresponding geo bin for the era
                    geo_bin_points[geo_bin][int(era)] += points

    # Compute average, median, and 10th percentile of performance points for each geo bin for each era
    for geo_bin, bin_eras_points in geo_bin_points.items():
        points = list(bin_eras_points.values())
        average_points = np.mean(points)
        median_points = np.median(points)
        percentile_10_points = np.percentile(points, 10)

        print(f"For geo bin `{geo_bin}` over the last {eras} eras:")
        print(f"Average total points: {average_points}")
        print(f"Median total points: {median_points}")
        print(f"10th percentile of total points: {percentile_10_points}\n")

if __name__ == "__main__":
    main()
