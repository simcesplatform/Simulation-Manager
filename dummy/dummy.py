# -*- coding: utf-8 -*-

"""This module contains a dummy simulation component that has very simple internal logic."""

import asyncio
import random
import sys
from typing import cast, Any, Union

from dummy.random_series import get_all_random_series, get_latest_values, get_random_initial_values
from tools.clients import RabbitmqClient
from tools.messages import AbstractMessage, EpochMessage, ErrorMessage, ResultMessage, StatusMessage, \
                           SimulationStateMessage, get_next_message_id
from tools.tools import FullLogger, load_environmental_variables

LOGGER = FullLogger(__name__)

# The time interval in seconds that is waited before closing after receiving simulation state message "stopped".
TIMEOUT_INTERVAL = 10

# The names of the environmental variables used by the component.
__SIMULATION_ID = "SIMULATION_ID"
__SIMULATION_COMPONENT_NAME = "SIMULATION_COMPONENT_NAME"
__SIMULATION_EPOCH_MESSAGE_TOPIC = "SIMULATION_EPOCH_MESSAGE_TOPIC"
__SIMULATION_STATUS_MESSAGE_TOPIC = "SIMULATION_STATUS_MESSAGE_TOPIC"
__SIMULATION_STATE_MESSAGE_TOPIC = "SIMULATION_STATE_MESSAGE_TOPIC"
__SIMULATION_ERROR_MESSAGE_TOPIC = "SIMULATION_ERROR_MESSAGE_TOPIC"
__SIMULATION_RESULT_MESSAGE_TOPIC = "SIMULATION_RESULT_MESSAGE_TOPIC"

__MIN_SLEEP_TIME = "MIN_SLEEP_TIME"
__MAX_SLEEP_TIME = "MAX_SLEEP_TIME"

__ERROR_CHANCE = "ERROR_CHANCE"
__SEND_MISS_CHANCE = "SEND_MISS_CHANCE"
__RECEIVE_MISS_CHANCE = "RECEIVE_MISS_CHANCE"
__WARNING_CHANCE = "WARNING_CHANCE"


class DummyComponent:
    """Class for holding the state of a dummy simulation component."""
    SIMULATION_STATE_VALUE_RUNNING = SimulationStateMessage.SIMULATION_STATES[0]   # "running"
    SIMULATION_STATE_VALUE_STOPPED = SimulationStateMessage.SIMULATION_STATES[-1]  # "stopped"

    def __init__(self, simulation_id: str, component_name: str, simulation_state_topic: str, epoch_topic: str,
                 status_topic: str, error_topic: str, result_topic: str, min_delay: float, max_delay: float,
                 error_chance: float, send_miss_chance: float, receive_miss_chance: float, warning_chance: float):
        self.__rabbitmq_client = RabbitmqClient()
        self.__simulation_id = simulation_id
        self.__component_name = component_name

        self.__simulation_state_topic = simulation_state_topic
        self.__epoch_topic = epoch_topic
        self.__status_topic = status_topic
        self.__error_topic = error_topic
        self.__result_topic = result_topic

        self.__min_delay = min_delay
        self.__max_delay = max_delay
        self.__error_chance = error_chance
        self.__send_miss_chance = send_miss_chance
        self.__receive_miss_chance = receive_miss_chance
        self.__warning_chance = warning_chance

        self.__simulation_state = DummyComponent.SIMULATION_STATE_VALUE_STOPPED
        self.__latest_epoch = 0
        self.__completed_epoch = 0
        self.__triggering_message_id = ""
        self.__last_status_message_id = None

        self.__message_id_generator = get_next_message_id(component_name)

        self.__rabbitmq_client.add_listener(
            [
                self.__simulation_state_topic,
                self.__epoch_topic
            ],
            self.general_message_handler)

        # Setup the first values of the randomly generated time series for the result messages.
        self.__last_result_values = get_random_initial_values()

    @property
    def simulation_id(self):
        """The simulation ID for the simulation."""
        return self.__simulation_id

    @property
    def component_name(self):
        """The component name in the simulation."""
        return self.__component_name

    async def stop(self):
        """Stops the component."""
        LOGGER.info("Stopping the component: '{:s}'".format(self.component_name))
        await self.set_simulation_state(DummyComponent.SIMULATION_STATE_VALUE_STOPPED)

    def get_simulation_state(self):
        """Returns the simulation state attribute."""
        return self.__simulation_state

    async def set_simulation_state(self, new_simulation_state: str):
        """Sets the simulation state. If the new simulation state is "running" and the current epoch is 0,
           sends a status message to the message bus.
           If the new simulation state is "stopped", stops the dummy component."""
        if new_simulation_state in SimulationStateMessage.SIMULATION_STATES:
            self.__simulation_state = new_simulation_state

            if new_simulation_state == DummyComponent.SIMULATION_STATE_VALUE_RUNNING:
                if self.__latest_epoch == 0:
                    await self.__send_new_status_message()

            elif new_simulation_state == DummyComponent.SIMULATION_STATE_VALUE_STOPPED:
                LOGGER.info("Component {:s} stopping in {:d} seconds.".format(
                    self.__component_name, TIMEOUT_INTERVAL))
                await asyncio.sleep(TIMEOUT_INTERVAL)
                sys.exit()

    async def start_epoch(self, epoch_number: int, start_time: str, end_time: str):
        """Starts a new epoch for the component. Sends a status message when finished."""
        if self.__simulation_state == DummyComponent.SIMULATION_STATE_VALUE_RUNNING:
            self.__latest_epoch = epoch_number

            # If the epoch is already completed, send a new status message immediately.
            if self.__completed_epoch == epoch_number:
                LOGGER.debug("Resending status message for epoch {:d}".format(epoch_number))
                await self.__send_new_status_message()
                return

            # Simulate an error possibility by using the random error chanche setting.
            rand_error_chance = random.random()
            if rand_error_chance < self.__error_chance:
                LOGGER.error("Encountered a random error.")
                await self.__send_error_message("Random error")

            # No errors, do normal epoch handling.
            else:
                rand_wait_time = random.uniform(self.__min_delay, self.__max_delay)
                LOGGER.info("Component {:s} sending status message for epoch {:d} in {:f} seconds.".format(
                    self.__component_name, self.__latest_epoch, rand_wait_time))
                await asyncio.sleep(rand_wait_time)

                await self.__send_random_result_message(start_time, end_time)
                await self.__send_new_status_message()

    async def general_message_handler(self, message_object: Union[AbstractMessage, Any], message_routing_key: str):
        """Forwards the message handling to the appropriate function depending on the message type."""
        if isinstance(message_object, SimulationStateMessage):
            await self.simulation_state_message_handler(message_object, message_routing_key)
            return

        if isinstance(message_object, EpochMessage):
            if random.random() < self.__receive_miss_chance:
                # Simulate a connection error by not receiving an epoch message.
                LOGGER.warning("Received message was ignored.")
                return
            await self.epoch_message_handler(message_object, message_routing_key)

        else:
            LOGGER.warning("Received '{:s}' message when expecting for '{:s}' or '{:s}' message".format(
                str(type(message_object)), str(SimulationStateMessage), str(EpochMessage)))

    async def simulation_state_message_handler(self, message_object: SimulationStateMessage, message_routing_key: str):
        """Handles the received simulation state messages."""
        if message_object.simulation_id != self.simulation_id:
            LOGGER.info(
                "Received state message for a different simulation: '{:s}' instead of '{:s}'".format(
                    message_object.simulation_id, self.simulation_id))
        elif message_object.message_type != SimulationStateMessage.CLASS_MESSAGE_TYPE:
            LOGGER.info(
                "Received a state message with wrong message type: '{:s}' instead of '{:s}'".format(
                    message_object.message_type, SimulationStateMessage.CLASS_MESSAGE_TYPE))
        else:
            LOGGER.debug("Received a state message from {:s} on topic {:s}".format(
                message_object.source_process_id, message_routing_key))
            self.__triggering_message_id = message_object.message_id
            await self.set_simulation_state(message_object.simulation_state)

    async def epoch_message_handler(self, message_object: EpochMessage, message_routing_key: str):
        """Handles the received epoch messages."""
        if message_object.simulation_id != self.simulation_id:
            LOGGER.info(
                "Received epoch message for a different simulation: '{:s}' instead of '{:s}'".format(
                    message_object.simulation_id, self.simulation_id))
        elif message_object.message_type != EpochMessage.CLASS_MESSAGE_TYPE:
            LOGGER.info(
                "Received a epoch message with wrong message type: '{:s}' instead of '{:s}'".format(
                    message_object.message_type, EpochMessage.CLASS_MESSAGE_TYPE))
        elif (message_object.epoch_number == self.__latest_epoch and
              self.__last_status_message_id in message_object.triggering_message_ids):
            LOGGER.info("Status message has already been registered for epoch {:d}".format(self.__latest_epoch))
        else:
            LOGGER.debug("Received an epoch from {:s} on topic {:s}".format(
                message_object.source_process_id, message_routing_key))
            self.__triggering_message_id = message_object.message_id

            await self.start_epoch(message_object.epoch_number, message_object.start_time, message_object.end_time)

    async def __send_new_status_message(self):
        """Sends a new status message to the message bus."""
        new_status_message = self.__get_status_message()
        if new_status_message is None:
            await self.__send_error_message("Internal error when creating status message.")
            return

        if self.__latest_epoch > 0 and random.random() < self.__send_miss_chance:
            # simulate connection error by not sending the status message for an epoch
            LOGGER.warning("No status message sent this time.")
        else:
            await self.__rabbitmq_client.send_message(self.__status_topic, new_status_message)

        self.__completed_epoch = self.__latest_epoch

    async def __send_error_message(self, description: str):
        """Sends an error message to the message bus."""
        error_message = self.__get_error_message(description)
        if error_message is None:
            # So serious error that even the error message could not be created => stop the component.
            await self.stop()

        else:
            await self.__rabbitmq_client.send_message(self.__error_topic, error_message)

    async def __send_random_result_message(self, start_time: str, end_time: str):
        """Sends a result message with random values and time series to the message bus."""
        random_result_message = self.__get_result_message(start_time, end_time)
        if random_result_message is None:
            await self.__send_error_message("Internal error when creating result message.")
        else:
            await self.__rabbitmq_client.send_message(self.__result_topic, random_result_message)

    def __get_status_message(self) -> Union[bytes, None]:
        """Creates a new status message and returns it in bytes format.
           Returns None, if there was a problem creating the message."""
        status_message = StatusMessage(**{
            "Type": StatusMessage.CLASS_MESSAGE_TYPE,
            "SimulationId": self.simulation_id,
            "SourceProcessId": self.component_name,
            "MessageId": next(self.__message_id_generator),
            "EpochNumber": self.__latest_epoch,
            "TriggeringMessageIds": [self.__triggering_message_id],
            "Value": StatusMessage.STATUS_VALUES[0]
        })
        if status_message is None:
            LOGGER.error("Problem with creating a status message")
            return None

        if random.random() < self.__warning_chance:
            LOGGER.debug("Adding a warning to the status message.")
            status_message.warnings = ["warning.internal"]

        self.__last_status_message_id = status_message.message_id
        return status_message.bytes()

    def __get_error_message(self, description: str) -> Union[bytes, None]:
        """Creates a new error message and returns it in bytes format.
           Returns None, if there was a problem creating the message."""
        error_message = ErrorMessage(**{
            "Type": ErrorMessage.CLASS_MESSAGE_TYPE,
            "SimulationId": self.simulation_id,
            "SourceProcessId": self.component_name,
            "MessageId": next(self.__message_id_generator),
            "EpochNumber": self.__latest_epoch,
            "TriggeringMessageIds": [self.__triggering_message_id],
            "Description": description
        })
        if error_message is None:
            LOGGER.error("Problem with creating an error message")
            return None

        return error_message.bytes()

    def __get_result_message(self, start_time: str, end_time: str) -> Union[bytes, None]:
        """Creates a new result message and returns it in bytes format.
           Returns None, if there was a problem creating the message."""
        result_message = ResultMessage.from_json({
            "Type": ResultMessage.CLASS_MESSAGE_TYPE,
            "SimulationId": self.simulation_id,
            "SourceProcessId": self.component_name,
            "MessageId": next(self.__message_id_generator),
            "EpochNumber": self.__latest_epoch,
            "TriggeringMessageIds": [self.__triggering_message_id]
        })
        if result_message is None:
            LOGGER.error("Problem with creating a result message")
            return None

        new_random_series_collection = get_all_random_series(self.__last_result_values, start_time, end_time)
        self.__last_result_values = get_latest_values(new_random_series_collection)

        result_message.result_values = new_random_series_collection
        return result_message.bytes()


async def start_dummy_component():
    """Start a dummy component for the simulation platform."""

    # Load the environmental variables to a dictionary.
    env_variables = load_environmental_variables(
        (__SIMULATION_ID, str),
        (__SIMULATION_COMPONENT_NAME, str, "dummy"),
        (__SIMULATION_EPOCH_MESSAGE_TOPIC, str, "epoch"),
        (__SIMULATION_STATUS_MESSAGE_TOPIC, str, "status"),
        (__SIMULATION_STATE_MESSAGE_TOPIC, str, "state"),
        (__SIMULATION_ERROR_MESSAGE_TOPIC, str, "error"),
        (__SIMULATION_RESULT_MESSAGE_TOPIC, str, "result"),
        (__MIN_SLEEP_TIME, float, 2),
        (__MAX_SLEEP_TIME, float, 15),
        (__ERROR_CHANCE, float, 0.0),
        (__SEND_MISS_CHANCE, float, 0.0),
        (__RECEIVE_MISS_CHANCE, float, 0.0),
        (__WARNING_CHANCE, float, 0.0)
    )

    DummyComponent(
        simulation_id=cast(str, env_variables[__SIMULATION_ID]),
        component_name=cast(str, env_variables[__SIMULATION_COMPONENT_NAME]),
        simulation_state_topic=cast(str, env_variables[__SIMULATION_STATE_MESSAGE_TOPIC]),
        epoch_topic=cast(str, env_variables[__SIMULATION_EPOCH_MESSAGE_TOPIC]),
        status_topic=cast(str, env_variables[__SIMULATION_STATUS_MESSAGE_TOPIC]),
        error_topic=cast(str, env_variables[__SIMULATION_ERROR_MESSAGE_TOPIC]),
        result_topic=cast(str, env_variables[__SIMULATION_RESULT_MESSAGE_TOPIC]),
        min_delay=cast(float, env_variables[__MIN_SLEEP_TIME]),
        max_delay=cast(float, env_variables[__MAX_SLEEP_TIME]),
        error_chance=cast(float, env_variables[__ERROR_CHANCE]),
        send_miss_chance=cast(float, env_variables[__SEND_MISS_CHANCE]),
        receive_miss_chance=cast(float, env_variables[__RECEIVE_MISS_CHANCE]),
        warning_chance=cast(float, env_variables[__WARNING_CHANCE]))

    # Wait in an endless loop until the DummyComponent is stopped and sys.exit() is called.
    while True:
        await asyncio.sleep(10 * TIMEOUT_INTERVAL)


if __name__ == "__main__":
    asyncio.run(start_dummy_component())
