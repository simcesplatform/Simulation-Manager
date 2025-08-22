# -*- coding: utf-8 -*-
# Copyright 2021 Tampere University and VTT Technical Research Centre of Finland
# This software was developed as a part of the ProCemPlus project: https://www.senecc.fi/projects/procemplus
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""This module contains a listener simulation component that prints out all messages from the message bus."""

import asyncio

from tools.clients import RabbitmqClient
from tools.message.abstract import BaseMessage
from tools.messages import AbstractMessage
from tools.tools import FullLogger, load_environmental_variables

LOGGER = FullLogger(__name__)

__SIMULATION_ID = "SIMULATION_ID"


class ListenerComponent:
    """Class for the message bus listener component."""
    LISTENED_TOPICS = "#"

    def __init__(self, rabbitmq_client: RabbitmqClient, simulation_id: str):
        self.__rabbitmq_client = rabbitmq_client
        self.__simulation_id = simulation_id

        self.__rabbitmq_client.add_listener(ListenerComponent.LISTENED_TOPICS, self.simulation_message_handler)

    @property
    def simulation_id(self):
        """The simulation ID for the simulation."""
        return self.__simulation_id

    async def simulation_message_handler(self, message_object: BaseMessage | dict | str, message_routing_key: str):  # noqa
        """Handles the received simulation state messages."""
        if isinstance(message_object, AbstractMessage):
            if message_object.simulation_id != self.simulation_id:
                LOGGER.info(
                    f"Received state message for a different simulation: '{message_object.simulation_id}' " +
                    f"instead of '{self.simulation_id}'")
            else:
                LOGGER.info(f"{message_routing_key} : {message_object.json()}")

        else:
            LOGGER.warning(f"Received '{type(message_object)}' message when expecting for '{AbstractMessage}' message")


async def start_listener_component():
    """Start a listener component for the simulation platform."""
    env_variables = load_environmental_variables(
        (__SIMULATION_ID, str)
    )

    simulation_id = env_variables[__SIMULATION_ID]
    if not isinstance(simulation_id, str):
        LOGGER.error("No simulation id found.")
        return

    ListenerComponent(RabbitmqClient(), simulation_id)
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(start_listener_component())
