# -*- coding: utf-8 -*-
# Copyright 2025 Tampere University and VTT Technical Research Centre of Finland
# This software was developed as a part of the ProCemPlus project: https://www.senecc.fi/projects/procemplus
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>
#            Otto Hylli <otto.hylli@tuni.fi>

"""This is the main script to run all the unit tests for the simulation-tools package."""

import unittest
import asyncio


def main():
    """Main function to run all the unit tests."""
    # Ensure an event loop is available
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover('.', pattern='*.py')
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == '__main__':
    main()
