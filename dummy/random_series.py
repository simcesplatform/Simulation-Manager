# -*- coding: utf-8 -*-

"""This module contains a function that can be used to generate random series of numbers."""

import random
from typing import Dict, List, Union

from tools.datetime_tools import to_utc_datetime_object
from tools.timeseries import TimeSeriesAttribute, TimeSeriesBlock

ATTRIBUTE_TYPE_SIMPLE = "simple"
ATTRIBUTE_TYPE_TIMESERIES = "timeseries"
N_DIGITS = 1

# These settings are used in determining the composition of the result messages in the dummy components.
RANDOM_ATTRIBUTES = {
    "DummyValue": {
        "type": ATTRIBUTE_TYPE_SIMPLE,
        "min": 0,
        "max": 1000
    },
    "TestValue": {
        "type": ATTRIBUTE_TYPE_SIMPLE,
        "min": 100,
        "max": 200
    },
    "Current": {
        "type": ATTRIBUTE_TYPE_TIMESERIES,
        "sub_types": ["L1", "L2", "L3"],
        "unit": "A",
        "min": 0.0,
        "max": 100.0,
        "max_difference": 5.0,
        "time_parts": 6
    },
    "Voltage": {
        "type": ATTRIBUTE_TYPE_TIMESERIES,
        "sub_types": ["L1", "L2", "L3"],
        "unit": "V",
        "min": 150.0,
        "max": 300.0,
        "max_difference": 10.0,
        "time_parts": 6
    }
}


def get_random_initial_values() -> Dict[str, Dict[str, float]]:
    """Returns randomly chosen initial values for the random time series attributes."""
    initial_values = {}
    for random_attribute_name, random_attribute_definition in RANDOM_ATTRIBUTES.items():
        if random_attribute_definition["type"] == ATTRIBUTE_TYPE_TIMESERIES:
            initial_values[random_attribute_name] = {}
            for sub_type in random_attribute_definition["sub_types"]:
                initial_values[random_attribute_name][sub_type] = round(
                    random.uniform(random_attribute_definition["min"], random_attribute_definition["max"]), N_DIGITS)

    return initial_values


def get_random_series(random_series_length: int, start_value: float, min_value: float, max_value: float,
                      max_difference: float) -> List[float]:
    """Returns a list of random numbers."""
    random_series = [start_value]
    previous_value = start_value
    for _ in range(random_series_length):
        new_value = round(
            random.uniform(
                max(previous_value - max_difference, min_value),
                min(previous_value + max_difference, max_value)),
            N_DIGITS)
        random_series.append(new_value)
        previous_value = new_value

    return random_series


def get_random_time_series(random_attribute_name: str, start_values: Dict[str, float],
                           start_time: str, end_time: str) -> Union[TimeSeriesBlock, None]:
    """Returns a randomly generated time series block for a result message."""
    random_attribute_definition = RANDOM_ATTRIBUTES.get(random_attribute_name, None)
    if random_attribute_definition is None or random_attribute_definition["type"] != ATTRIBUTE_TYPE_TIMESERIES:
        return None

    random_series_collection = {}
    for sub_attribute in random_attribute_definition["sub_types"]:
        new_random_series = get_random_series(
            random_series_length=random_attribute_definition["time_parts"],
            start_value=start_values[sub_attribute],
            min_value=random_attribute_definition["min"],
            max_value=random_attribute_definition["max"],
            max_difference=random_attribute_definition["max_difference"])
        start_values[sub_attribute] = new_random_series[-1]

        random_series_collection[sub_attribute] = TimeSeriesAttribute(
            UnitOfMeasure=random_attribute_definition["unit"],
            Values=new_random_series)

    start_time_object = to_utc_datetime_object(start_time)
    end_time_object = to_utc_datetime_object(end_time)
    time_step = (end_time_object - start_time_object) / random_attribute_definition["time_parts"]
    time_index = [
        start_time_object + index * time_step
        for index in range(0, random_attribute_definition["time_parts"] + 1)
    ]

    return TimeSeriesBlock(
        TimeIndex=time_index,
        Series=random_series_collection)


def get_all_random_series(start_values: Dict[str, Dict[str, float]],
                          start_time: str, end_time: str) -> Dict[str, Union[float, TimeSeriesBlock]]:
    """Returns a dictionary containing new random values for all the defined random attributes."""
    new_series_collection = {}
    for random_attribute_name, random_attribute_definition in RANDOM_ATTRIBUTES.items():
        if random_attribute_definition["type"] == ATTRIBUTE_TYPE_SIMPLE:
            new_series_collection[random_attribute_name] = round(
                random.uniform(random_attribute_definition["min"], random_attribute_definition["max"]), N_DIGITS)
        else:
            new_random_series = get_random_time_series(
                random_attribute_name, start_values[random_attribute_name], start_time, end_time)
            if isinstance(new_random_series, TimeSeriesBlock):
                new_series_collection[random_attribute_name] = new_random_series

    return new_series_collection


def get_latest_values(random_series_collection: Dict[str, Union[float, TimeSeriesBlock]]) \
        -> Dict[str, Dict[str, float]]:
    """Returns a dictionary containing the latest values for all the series in the collection."""
    latest_values = {}
    for attribute_name, attribute_values in random_series_collection.items():
        if isinstance(attribute_values, TimeSeriesBlock):
            latest_values[attribute_name] = {}
            for series_name, series_values in attribute_values.series.items():
                if series_values.values:
                    latest_values[attribute_name][series_name] = series_values.values[-1]

    return latest_values
