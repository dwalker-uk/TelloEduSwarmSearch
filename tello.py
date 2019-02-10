import time


class Tello:
    """ Holds details about each individual Tello """

    #
    # CLASS INIT
    #

    def __init__(self, ip):
        """ Keep track of the IP, SN and Num of each Tello, plus its command_queue and log """
        self.ip = ip
        self.sn = None
        self.num = 0
        self.max_cmd_id = 0
        self.command_queue = []
        self.log = []
        self.flight_complete = False
        self.status = {}

    #
    # COMMAND_QUEUE AND LOG MANAGEMENT
    #

    def add_to_command_queue(self, command, command_type, on_error):
        """ Queues commands, which will be sent via the command_handler thread as soon as the Tello is ready.

            Each command in the queue is given a cmd_id, an increasing index, which is then carried over to the log -
             this allows commands and their responses to be tracked and tested reliable.
            Will not allow any new commands to be added to the queue once marked as flight_complete!
            :param command: The actual command from Tello SDK, e.g. 'battery?', 'forward 50', etc...
            :param command_type: Either 'Control', 'Set' or 'Read' - corresponding to the Tello SDK documentation.
            :param on_error: An alternative Tello SDK string to be sent if command returns an error.
            :return: The cmd_id for this new entry in the queue, to allow calling functions to track the response.
        """
        if not self.flight_complete:
            self.max_cmd_id += 1
            self.command_queue.append(TelloCommand(self.max_cmd_id, command, command_type, on_error))
            return self.max_cmd_id
        else:
            return -1

    def add_to_log(self, cmd_id, command, command_type, on_error):
        """ Logs commands; usually having just been taken out of the command_queue.

            :param cmd_id: The cmd_id that was previously assigned in the command_queue.
            :param command: The actual command from Tello SDK, e.g. 'battery?', 'forward 50', etc...
            :param command_type: Either 'Control', 'Set' or 'Read' - corresponding to the Tello SDK documentation.
            :param on_error: An alternative Tello SDK string to be sent if command returns an error, or None.
            :return: The new log entry (as a TelloCommand instance)
        """
        new_log_entry = TelloCommand(cmd_id, command, command_type, on_error)
        self.log.append(new_log_entry)
        return new_log_entry

    def log_entry(self, cmd_id=None, timeout=10):
        """ Return the log entry for specified cmd_id, or latest if cmd_id is None.

            :param cmd_id: The cmd_id of the log entry we're looking for, or None for the last entry.
            :param timeout: Max seconds to wait if log entry doesn't exist yet, i.e. command hasn't yet been sent.
            :return: Returns the corresponding log entry, which will be a TelloCommand instance.
        """
        return self._get_log_entry(cmd_id, timeout)

    #
    # PENDING RESPONSE
    #

    def wait_until_idle(self):
        """ Blocking method, will only return once command_queue is empty and the last response is received. """
        # TODO: Add timeout to this method?
        while self.command_queue:
            time.sleep(0.05)
        while self.log[-1].response is None:
            time.sleep(0.05)

    def log_wait_response(self, cmd_id=None, timeout=10):
        """ Blocking method, will return log entry once it's been sent and response is received.

            :param cmd_id: The cmd_id of the log entry we're looking for, or None for the last entry.
            :param timeout: Max seconds to wait for response.
            :return: Returns the corresponding log entry, which will be a TelloCommand instance.
        """
        log_entry = self._get_log_entry(cmd_id, timeout)
        while log_entry.response is None:
            # Sleep briefly whilst waiting for response, to prevent excessive CPU usage
            time.sleep(0.01)
        return log_entry

    #
    # PRIVATE HELPER METHODS
    #

    def _get_log_entry(self, cmd_id, timeout):
        """ Returns a log entry (TelloCommand object), either matching the cmd_id or else the latest log entry.

            This is a blocking function, that will wait max timeout secs for the log to become available, i.e. for the
             command to be sent!

            :param cmd_id: Either the cmd_id of the entry we want, or None, which will return the most recent log entry.
            :param timeout: Max seconds to wait for response, before raising an error.
            :return: Returns the corresponding log entry, which will be a TelloCommand object.
        """
        if cmd_id is None:
            return self.log[-1]
        else:
            timeout_start = time.time()
            while time.time() - timeout_start < timeout:
                for log in self.log:
                    if log.cmd_id == cmd_id:
                        return log
                # Sleep briefly at the end of each loop, to prevent excessive CPU usage
                time.sleep(0.01)
            raise RuntimeError('Tello log entry not found!!')


class TelloCommand:
    """ Simple class holding data associated with individual commands - used for both command_queue and log. """

    def __init__(self, cmd_id, command, command_type, on_error):
        """ Create a new instance, with key fields populated at the start.  response and success are updated later.

            :param cmd_id: An integer to uniquely identify this command.
            :param command: The actual command from Tello SDK, e.g. 'battery?', 'forward 50', etc...
            :param command_type: Either 'Control', 'Set' or 'Read' - corresponding to the Tello SDK documentation.
            :param on_error: An alternative Tello SDK string to be sent if command returns an error, or None.
        """
        self.cmd_id = cmd_id
        self.command = command
        self.command_type = command_type
        self.response = None
        self.success = None
        self.on_error = on_error
