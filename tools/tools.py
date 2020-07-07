# -*- coding: utf-8 -*-

"""Common tools for the use of Omega and Simulation Manager."""

import datetime
import logging
import os


class EnvironmentVariable:
    """Class for accessing and holding environment information."""

    def __init__(self, variable_name: str, variable_type=str, default_value=""):
        self.__variable_name = variable_name
        self.__variable_type = variable_type
        self.__default_value = default_value

        self.__value_fetched = False
        self.__value = default_value

    @property
    def variable_name(self):
        """Return the variable name."""
        return self.__variable_name

    @property
    def variable_type(self):
        """Returns the variable type."""
        return self.__variable_type

    @property
    def default_value(self):
        """Returns the default value for the variable."""
        return self.__default_value

    @property
    def value(self):
        """Returns the value of the environmental value.
           The value is only fetched from the environment at the first call."""
        if not self.__value_fetched:
            new_value = os.environ.get(self.variable_name, self.default_value)

            if self.variable_type is datetime.datetime:
                self.__value = datetime.datetime.fromisoformat(new_value.replace("Z", "+00:00"))
            elif self.variable_type is bool and isinstance(new_value, str):
                self.__value = new_value.lower() == "true"
            else:
                self.__value = self.variable_type(new_value)
            self.__value_fetched = True
        return self.__value

    def __str__(self):
        """Returns the string representation of the variable name and value."""
        return "{:s}: {:s}".format(self.variable_name, str(self.value))


class EnvironmentVariables:
    """A class for accessing several environment variables."""

    def __init__(self, *variables):
        self.__variables = dict()
        for variable in variables:
            self.add_variable(variable)

    def add_variable(self, new_variable):
        """Adds new variable to the variable list."""
        if isinstance(new_variable, (list, tuple)) and new_variable:
            self.__variables[new_variable[0]] = EnvironmentVariable(*new_variable)
        elif isinstance(new_variable, EnvironmentVariable):
            self.__variables[new_variable] = new_variable
        else:
            self.__variables[new_variable] = EnvironmentVariable(new_variable)

    def get_variables(self):
        """Returns a list of the registered environment variable names."""
        return list(self.__variables.keys())

    def get_value(self, variable_name):
        """Returns the value of the wanted environmental parameter.
           The value for each parameter is only fetched from the environment at the first call."""
        if variable_name in self.__variables:
            return self.__variables[variable_name].value
        FILE_LOGGER.info("Environment variable %s not registered.", variable_name)
        return None


def load_environmental_variables(*env_variable_specifications):
    """Returns the realized environmental variable values as a dictionary."""
    env_variables = EnvironmentVariables(*env_variable_specifications)
    return {
        variable_name: env_variables.get_value(variable_name)
        for variable_name in env_variables.get_variables()
    }


COMMON_ENV_VARIABLES = load_environmental_variables(
    ("SIMULATION_LOG_LEVEL", int, logging.DEBUG),
    ("SIMULATION_LOG_FILE", str, "logfile.log"),
    ("SIMULATION_LOG_FORMAT", str, " --- ".join([
        "%(asctime)s",
        "%(levelname)s",
        "%(name)s",
        "%(funcName)s",
        "%(message)s"])
    )
)

def get_logger(logger_name):
    """Returns a logger object."""
    new_logger = logging.getLogger(logger_name)
    new_logger.setLevel(COMMON_ENV_VARIABLES["SIMULATION_LOG_LEVEL"])

    log_file_handler = logging.FileHandler(COMMON_ENV_VARIABLES["SIMULATION_LOG_FILE"])
    log_file_handler.setFormatter(logging.Formatter(COMMON_ENV_VARIABLES["SIMULATION_LOG_FORMAT"]))
    new_logger.addHandler(log_file_handler)

    return new_logger


FILE_LOGGER = get_logger(__name__)