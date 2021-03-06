import json
import os
import pandas as pd
import numpy as np

from .helpers.commands import get_commands_from_file
from .helpers.time import get_shop_timestring
from .shopcore.model_builder import ModelBuilderType
from .shopcore.command_builder import CommandBuilder, get_derived_command_key
from .shopcore.shop_api import get_time_resolution


class ShopSession(object):
    # Class for handling a SHOP session through the python API.

    def __init__(self, license_path='', silent=True, log_file='', solver_path='', suppress_log=False, log_gets=True, name='unnamed', id=1):
        # Initialize a new SHOP session
        #
        # @param license_path The path where the license file, solver and solver interface are located
        self._license_path = license_path
        self._silent = silent
        self._log_file = log_file
        self._solver_path = solver_path
        self._suppress_log = suppress_log
        self._log_gets = log_gets
        self._name = name
        self._id = id

        if license_path:
            os.environ['ICC_COMMAND_PATH'] = license_path
        import pyshop.shop_pybind as pb
        silent_console = silent
        silent_log = suppress_log
        if log_file:
            self.shop_api = pb.ShopCore(silent_console, silent_log, log_file, log_gets)
        else:
            self.shop_api = pb.ShopCore(silent_console, silent_log)
        if solver_path:
            abs_path = os.path.abspath(solver_path)
            self.shop_api.OverrideDllPath(abs_path)
        if solver_path:
            abs_path = os.path.abspath(solver_path)
            self.shop_api.OverrideDllPath(abs_path)
        self.model = ModelBuilderType(self.shop_api)
        self._commands = {x.replace(' ', '_'): x for x in self.shop_api.GetCommandTypesInSystem()}
        self._all_messages = []
        self._command = None

    def __dir__(self):
        return list(self._commands.keys()) + [x for x in super().__dir__() if x[0] != '_' 
                                              and x not in self._commands.keys()]

    def __getattr__(self, command):
        self._command = command.lower()
        return self._execute_command

    def _execute_command(self, options, values):
        self._command = get_derived_command_key(self._command, self._commands)
        if self._command not in self._commands:
            raise ValueError(f'Unknown command: "{self._command.replace("_", " ")}"')
        if not isinstance(options, list):
            options = [options]
        if not isinstance(values, list):
            values = [values]
        options = map(str, options)
        options = filter(lambda x: x, options)
        values = map(str, values)
        values = filter(lambda x: x, values)
        return self.shop_api.ExecuteCommand(self._commands[self._command], list(options), list(values))

    def set_time_resolution(self, starttime, endtime, timeunit, timeresolution=None):
        # Reformat timestamps to format expected by Shop
        start_string = get_shop_timestring(starttime)
        end_string = get_shop_timestring(endtime)

        # Handle time resolution
        # Constant
        if not isinstance(timeresolution, pd.DataFrame) and not isinstance(timeresolution, pd.Series):
            self.shop_api.SetTimeResolution(start_string, end_string, timeunit)
        # Timestamp indexed
        elif isinstance(timeresolution.index, pd.DatetimeIndex):
            # Handle time horizon outside time resolution definition
            if timeresolution.loc[starttime:starttime].empty:
                timeresolution.loc[starttime] = np.nan
                timeresolution.sort_index(inplace=True)
                timeresolution.ffill(inplace=True)
            timeresolution = timeresolution[starttime:endtime]
            # Transform timestamp index to integer index expected by Shop
            timeunit_delta = pd.Timedelta(hours=1) if timeunit == 'hour' else pd.Timedelta(minutes=1)
            timeres_t = [int((t - starttime) / timeunit_delta) for t in timeresolution.index]
            self.shop_api.SetTimeResolution(start_string, end_string, timeunit, timeres_t, timeresolution.values)
        # Integer indexed
        else:
            timeres_t = timeresolution.index.values
            self.shop_api.SetTimeResolution(start_string, end_string, timeunit, timeres_t, timeresolution.values)
    
    def get_time_resolution(self):
        # Get time resolution
        return get_time_resolution(self.shop_api)

    def get_messages(self, all_messages=False):
        # Get all new messages from the buffer as a dict.
        messages = self.shop_api.GetMessages()
        messages = json.loads(messages)

        self._all_messages.extend(messages)

        if all_messages:
            return self._all_messages
        else:
            return messages

    def execute_full_command(self, full_command):
        parts = full_command.lower().strip().split()
        # First try to get a match using the two first words
        first_non_command = 2
        try:
            command = get_derived_command_key(parts[0] + '_' + parts[1], self._commands)
        except ValueError as err:
            try:
                command = get_derived_command_key(parts[0], self._commands)
                first_non_command = 1
            except ValueError as err2:
                error_message = "Could not find any a single command match. Got the following errors:\n" + str(err) + \
                                '\n' + str(err2)
                raise ValueError(error_message)

        parts = parts[first_non_command:]
        options = []
        values = []
        for word in parts:
            if word[0] == '/':
                options.append(word[1:])
            else:
                values.append(word)
        self._command = command
        self._execute_command(options, values)

    def get_executed_commands(self):
        commands = self.shop_api.GetExecutedCommands()
        return commands

    def read_ascii_file(self, file_path):
        self.shop_api.ReadShopAsciiFile(file_path)

    def load_yaml(self, file_path='', yaml_string=''):
        if file_path != '' and yaml_string != '':
            raise ValueError('Provide either a file path or a yaml string, not both')
        if file_path != '':
            with open(file_path, 'r', encoding='utf8') as f:
                yaml_file_string = f.read()
            self.shop_api.ReadYamlString(yaml_file_string)
        elif yaml_string != '':
            self.shop_api.ReadYamlString(yaml_string)

    def dump_yaml(self, file_path='', input_only=False, compress_txy=False, compress_connection=False):
        if file_path != '':
            self.shop_api.DumpYamlCase(file_path, input_only, compress_txy, compress_connection)
            return f'YAML case is dumped to the provided file path: "{file_path}"'
        else:
            return self.shop_api.DumpYamlString(input_only, compress_txy, compress_connection)

    def run_command_file(self, folder, command_file):
        with open(os.path.join(folder, command_file), 'r', encoding='iso-8859-1') as run_file:
            file_string = run_file.read()
            run_commands = get_commands_from_file(file_string)
        for command in run_commands:
            self.shop_api.ExecuteCommand(command['command'], command['options'], command['values'])

    def run_command_file_progress(self, folder, command_file):
        with open(os.path.join(folder, command_file), 'r', encoding='iso-8859-1') as run_file:
            file_string = run_file.read()
            run_commands = get_commands_from_file(file_string)
        command_list = []
        options_list = []
        values_list = []
        for command in run_commands:
            command_list.append(command['command'])
            options_list.append(command['options'])
            values_list.append(command['values'])
        self.shop_api.ExecuteCommandList(command_list, options_list, values_list)

    def execute_command(self):
        # Terminal function for executing SHOP commands that gives code completion for SHOP commands.
        return CommandBuilder(self.shop_api)

    def get_shop_version(self):
        version_string = self.shop_api.GetVersionString()
        return version_string.split()[0]
