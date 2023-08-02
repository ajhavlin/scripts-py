import src.xxapi as xxapi
import numpy as np
from collections import defaultdict
import requests

def fetch_validator_rewards(xxchain, start_era, end_era):
    # Fetch validator information
    url = "https://dashboard-api.xx.network/v1/nodes"
    response = requests.get(url)
    data = response.json()

    validators_geo_bins = {}
    for node in data["nodes"]:
        if node['status'] != "not currently a validator":
            validators_geo_bins[node['walletAddress']] = node['geoBin']


    # Similar to staking_rewards but only gets points
    curr_era = xxchain.item_query("Staking", "ActiveEra")['index']
    if end_era > curr_era - 1:
        raise Exception("End era can't be larger than last era")

    # Gather necessary information for era range
    depth = xxchain.item_query("Staking", "HistoryDepth")
    points = {}
    target_era = start_era
    while True:
        eras_points = xxchain.query_era(target_era, xxchain.map_query, "Staking", "ErasRewardPoints", "")
        points = {**points, **eras_points}
        target_era += depth - 1
        if target_era >= end_era:
            break

    result = {"start_era": start_era, "end_era": end_era, "accounts": {}}

    for era in range(start_era, end_era+1):
        era_points = points[era]
        for validator, validator_points in era_points['individual']:
            if validator not in result["accounts"]:
                result["accounts"][validator] = {}
            result["accounts"][validator][era] = validator_points
            result["accounts"][validator]['geoBin'] = validators_geo_bins.get(validator, None)  # Add geo bin info

    return result

def main():
    # Connect to chain
    xxchain = xxapi.XXNetworkInterface("wss://xx.api.onfinality.io/public-ws")
    if xxchain is None:
        exit(1)

    eras = 7  # Specify the number of eras
    curr_era = xxchain.item_query("Staking", "ActiveEra")['index']
    end_era = curr_era - 1
    start_era = end_era - eras + 1

    # Fetch points data for all validators across the eras
    points_data = fetch_validator_rewards(xxchain, start_era, end_era)

    # Get performance points of validators and group them by geo bins
    geo_bin_points = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for validator, validator_info in points_data["accounts"].items():
        # Get geo bin for the validator
        geo_bin = validator_info.get('geoBin', None)
        if geo_bin is not None:
            validator_era_points = {key: value for key, value in validator_info.items() if key != 'geoBin'}
            for era, points in validator_era_points.items():
                # Add validator's points to the corresponding geo bin for the era
                geo_bin_points[geo_bin][validator][int(era)] = points

    validator_avg_points = defaultdict(lambda: defaultdict(int))

    # Compute average of performance points for each validator over the last 'n' eras
    for geo_bin, bin_validators_points in geo_bin_points.items():
        for validator, validator_era_points in bin_validators_points.items():
            points = list(validator_era_points.values())
            average_points = np.mean(points)
            # median_points = np.median(points)
            # percentile_10_points = np.percentile(points, 10)

            validator_avg_points[geo_bin][validator] = average_points

            # print(f"For geo bin `{geo_bin}` for validator `{validator}` over the last {eras} eras:")
            # print(f"Average total points: {average_points}")
            # print(f"Median total points: {median_points}")
            # print(f"10th percentile of total points: {percentile_10_points}\n")

    
    # Compute average, median, and 10th percentile of averaged performance points for each geo bin
    for geo_bin, geo_bin_validator_points in validator_avg_points.items():
        avg_points_list = list(geo_bin_validator_points.values())
        average_points = np.mean(avg_points_list)
        median_points = np.median(avg_points_list)
        percentile_10_points = np.percentile(avg_points_list, 10)
        percentile_90_points = np.percentile(avg_points_list, 90)

        print(f"\x1B[1m For geo bin `{geo_bin}` over the last {eras} eras: \x1B[0m")
        print(f"Average of average points: {average_points}")
        print(f"Median of average points: {median_points}")
        print(f"10th percentile of average points: {percentile_10_points}")
        print(f"90th percentile of average points: {percentile_90_points}\n")
        

if __name__ == "__main__":
    main()
