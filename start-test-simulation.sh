#!/bin/bash
# Copyright 2023 Tampere University and VTT Technical Research Centre of Finland
# This software was developed as a part of the ProCemPlus project: https://www.senecc.fi/projects/procemplus
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

if docker compose version >/dev/null 2>&1
then
    compose_command="docker compose"
else
    compose_command="docker-compose"
fi

source create_new_simulation_id.sh
$compose_command -f docker-compose-test-simulation.yml up --build
