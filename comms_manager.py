import socket
import netifaces
import netaddr
import threading
import time
from tello import Tello


class CommsManager:

    #
    # CLASS INIT & SETUP
    #

    def __init__(self):
        """ Open sockets ready for communicating with one or more Tellos.

            Also initiate the threads for receiving control messages and status from Tello.
            Also create the placeholder list for Tello objects.
        """

        self.terminate_comms = False

        # Socket for primary bi-directional communication with Tello
        self.control_port = 8889
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket for sending cmd
        self.control_socket.bind(('', self.control_port))

        # Socket for receiving status messages from Tello - not activated here
        self.status_port = 8890
        self.status_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.status_thread = None

        # Thread for receiving messages from Tello
        self.receive_thread = threading.Thread(target=self._receive_thread)
        self.receive_thread.daemon = True
        self.receive_thread.start()

        # Reference to all active Tellos
        self.tellos = []

    def init_tellos(self, sn_list, get_status=False, first_ip=1, last_ip=254):
        """ Search the network until found the specified number of Tellos, then get each Tello ready for use.

            This must be run once; generally the first thing after initiating CommsManager.
            The 'command' message is sent to every IP on the network, with the response_handler thread managing the
             responses to create Tello objects in self.tellos.
            A command_handler is then created for each, which manages the command_queue for each.
            Finally, each Tello is queried for its serial number, which is stored in the Tello object with its number.

            :param sn_list: List of serial numbers, in order we want to number the Tellos.
            :param get_status: True to listen for and record the status messages from the Tellos.
            :param first_ip: If known, we can specify a smaller range of IP addresses to speed up the search.
            :param last_ip: If known, we can specify a smaller range of IP addresses to speed up the search.
        """

        # Get network addresses to search
        subnets, address = self._get_subnets()
        possible_addr = []

        # Create a list of possible IP addresses to search
        for subnet, netmask in subnets:
            for ip in netaddr.IPNetwork('%s/%s' % (subnet, netmask)):
                if not (first_ip <= int(str(ip).split('.')[3]) <= last_ip):
                    continue
                # Don't add the server's address to the list
                if str(ip) in address:
                    continue
                possible_addr.append(str(ip))

        # Continue looking until we've found them all
        num = len(sn_list)
        while len(self.tellos) < num:
            print('[Tello Search]Looking for %d Tello(s)' % (num - len(self.tellos)))

            # Remove any found Tellos from the list to search
            for tello_ip in [tello.ip for tello in self.tellos]:
                if tello_ip in possible_addr:
                    possible_addr.remove(tello_ip)

            # Try contacting Tello via each possible_addr
            for ip in possible_addr:
                self.control_socket.sendto('command'.encode(), (ip, self.control_port))

            # Responses to the command above will be picked up in receive_thread.  Here we check regularly to see if
            #  they've all been found, so we can break out quickly.  But after several failed attempts, go around the
            #  whole loop again and retry contacting.
            for _ in range(0, 10):
                time.sleep(0.5)
                if len(self.tellos) >= num:
                    break

        # Once we have all Tellos, startup a command_handler for each.  These manage the command queues for each Tello.
        for tello in self.tellos:
            command_handler_thread = threading.Thread(target=self._command_handler, args=(tello,))
            command_handler_thread.daemon = True
            command_handler_thread.start()

        # Start the status_handler, if needed.  This receives and constantly updates the status of each Tello.
        if get_status:
            self.status_socket.bind(('', self.status_port))
            self.status_thread = threading.Thread(target=self._status_thread)
            self.status_thread.daemon = True
            self.status_thread.start()

        # Query each Tello to get its serial number - saving the cmd_id so we can match-up responses when they arrive
        tello_cmd_id = []
        for tello in self.tellos:
            # Save the tello together with the returned cmd_id, so we can match the responses with the right Tello below
            tello_cmd_id.append((tello, tello.add_to_command_queue('sn?', 'Read', None)))

        # Assign the sn to each Tello, as responses become available.
        # Note that log_wait_response will block until the response is received.
        for tello, cmd_id in tello_cmd_id:
            tello.sn = tello.log_wait_response(cmd_id).response
            # Once we know the SN, look it up in the supplied sn_list and assign the correct tello_num
            for index, sn in enumerate(sn_list, 1):
                if tello.sn == sn:
                    tello.num = index

        # Sort the list of Tellos by their num
        self.tellos.sort(key=lambda tello: tello.num)

    #
    # PUBLIC METHODS
    #

    def queue_command(self, command, command_type, tello_num, on_error=None):
        """ Add a new command to the Tello's (either one Tello or all) command queue - returning the cmd_id.

            Note that if a Tello is marked as flight_completed, it will return -1 as its cmd_id.  These are not
             added to the list returned here, so can effectively be ignored by calling functions.

            :param command: The Tello SDK string (e.g. 'forward 50' or 'battery?') to send to the Tello(s).
            :param command_type: Either 'Control', 'Set' or 'Read' - corresponding to the Tello SDK documentation.
            :param tello_num: Either 'All' or a Tello number (1,2,...)
            :param on_error: A different Tello SDK string to be sent if command returns an error.
            :return: A list of tuples in the form [(tello_num, cmd_id),...].
        """
        # Determine which Tellos to use, and add the command to the appropriate Tello's queue.
        cmd_ids = []
        if tello_num == 'All':
            for tello in self.tellos:
                # If command is for all tellos, send to each and save the cmd_id in a list
                cmd_id = tello.add_to_command_queue(command, command_type, on_error)
                if cmd_id != -1:
                    cmd_ids.append((tello.num, cmd_id))
        else:
            tello = self.get_tello(num=tello_num)
            cmd_id = tello.add_to_command_queue(command, command_type, on_error)
            if cmd_id != -1:
                cmd_ids.append((tello.num, cmd_id))
        return cmd_ids

    def wait_sync(self):
        """ Used to pause the main thread whilst all Tellos catch up, to bring all Tellos into sync.

            Simply checks with each Tello object that each individually has fully processed its queue and responses.
            The wait_until_idle command is a blocking function, so won't return until ready.
        """
        for tello in self.tellos:
            tello.wait_until_idle()

    def get_tello(self, num):
        """ Shortcut function to return a specific Tello instance, based on its number.

            :param num: Tello number, as an integer (e.g. 1,2,...)
            :return: Tello object
        """
        for tello in self.tellos:
            if tello.num == num:
                return tello
        raise RuntimeError('Tello not found!')

    def close_connections(self):
        """ Close all comms - to tidy up before exiting """
        self.terminate_comms = True
        self.control_socket.close()
        self.status_socket.close()

    #
    # PRIVATE HELPER METHODS
    #

    @staticmethod
    def _get_subnets():
        """ Get the local subnet and server IP address """
        subnets = []
        addr_list = []
        ifaces = netifaces.interfaces()
        for this_iface in ifaces:
            addrs = netifaces.ifaddresses(this_iface)

            if socket.AF_INET not in addrs:
                continue

            # Get IPv4 info
            ip_info = addrs[socket.AF_INET][0]
            address = ip_info['addr']
            netmask = ip_info['netmask']

            # Avoid searching when on very large subnets
            if netmask != '255.255.255.0':
                continue

            # Create IP object and get the network details
            # Note CIDR is a networking term, describing the IP/subnet address format
            cidr = netaddr.IPNetwork('%s/%s' % (address, netmask))
            network = cidr.network
            subnets.append((network, netmask))
            addr_list.append(address)
        return subnets, addr_list

    def _get_tello(self, ip):
        """ Private function to return the Tello object with the matching IP address.

            :param ip: IP address of the requested Tello object, as a string e.g. '123.45.678.90'
            :return: Tello object
        """
        for tello in self.tellos:
            if tello.ip == ip:
                return tello
        raise RuntimeError('Tello not found!')

    def _send_command(self, tello, cmd_id, command, command_type, on_error, timeout=10):
        """ Actually send a command to the Tello at specified IP address, recording details in the Tello's log.

            :param tello: The Tello object for which we're sending the command
            :param cmd_id: Corresponds to the id first given when in the Tello's queue, to be transferred to its log.
            :param command: The actual command from Tello SDK, e.g. 'battery?', 'forward 50', etc...
            :param command_type: Either 'Control', 'Set' or 'Read' - corresponding to the Tello SDK documentation.
            :param on_error: A different Tello SDK string to be sent if command returns an error.
        """

        # Add the command to the Tello's log first
        log_entry = tello.add_to_log(cmd_id, command, command_type, on_error)

        # Then send the command
        self.control_socket.sendto(command.encode(), (tello.ip, self.control_port))
        print('[Command  %s]Sent cmd: %s' % (tello.ip, command))

        # Wait until a response has been received, and handle timeout
        time_sent = time.time()
        while log_entry.response is None:
            now = time.time()
            if now - time_sent > timeout:
                print('[Command  %s]Failed to send: %s' % (tello.ip, command))
                log_entry.success = False
                log_entry.response = ''
                if log_entry.on_error is not None:
                    tello.add_to_command_queue(log_entry.on_error, log_entry.command_type, None)
                    print('[Command  %s]Queuing alternative cmd: %s' % (tello.ip, log_entry.on_error))
                return
            # Sleep briefly at the end of each loop, to prevent excessive CPU usage
            time.sleep(0.01)

    #
    # THREADS
    #

    def _command_handler(self, tello):
        """ Run Command Handler as a separate thread for each Tello, to manage the queue of commands.

            This runs as a separate thread so that applications can instantly add commands to multiple queues
            simultaneously, and then each of these threads (one per Tello) can all actually send the command
            together.  The send_command function called from here is a blocking function, which doesn't return
            until the response has been received or the command exceeds its timeout.

            :param tello: The Tello object with which the command_handler should be associated.
        """
        while True:
            # If nothing in the queue, just keep looping
            while not tello.command_queue:
                time.sleep(0.01)
            # Pop command off the Tello's queue, then send the command.
            # Note as part of send_command the same details will be added back into Tello's log.
            command = tello.command_queue.pop(0)
            self._send_command(tello, command.cmd_id, command.command, command.command_type, command.on_error)

    def _receive_thread(self):
        """ Listen continually to responses from the Tello - should run in its own thread.

            This method includes capturing and saving each Tello the first time it responds.
            If it is a known Tello, the response will be matched against the Tello's log, always recording the response
            against the last log entry as commands sent to each Tello are strictly sequential.
            Responses are also tested for success or failure, and if relevant an alternative command may be sent
            immediately on error.
        """

        while not self.terminate_comms:
            try:
                # Get responses from all Tellos - this line blocks until a message is received - and reformat values
                response, ip = self.control_socket.recvfrom(1024)
                response = response.decode().strip()
                ip = str(ip[0])

                # Capture Tellos when they respond for the first time
                if response.lower() == 'ok' and ip not in [tello.ip for tello in self.tellos]:
                    print('[Tello Search]Found Tello on IP %s' % ip)
                    self.tellos.append(Tello(ip))
                    continue

                # Get the current log entry for this Tello
                tello = self._get_tello(ip)
                log_entry = tello.log_entry()

                # Determine if the response was ok / error (or reading a value)
                send_on_error = False
                if log_entry.command_type in ['Control', 'Set']:
                    if response == 'ok':
                        log_entry.success = True
                    else:
                        log_entry.success = False
                        if log_entry.on_error is not None:
                            # If this command wasn't successful, and there's an on_error entry, flag to send it later.
                            send_on_error = True
                elif log_entry.command_type == 'Read':
                    # Assume Read commands are always successful... not aware they can return anything else!?
                    log_entry.success = True
                else:
                    print('[Response %s]Invalid command_type: %s' % (ip, log_entry.command_type))
                # Save .response *after* .success, as elsewhere we use .response as a check to move on - avoids race
                # conditions across the other running threads, which might otherwise try to use .success before saved.
                log_entry.response = response
                print('[Response %s]Received: %s' % (ip, response))
                # If required, queue the alternative command - assume same command type as the original.
                if send_on_error:
                    tello.add_to_command_queue(log_entry.on_error, log_entry.command_type, None)
                    print('[Command  %s]Queuing alternative cmd: %s' % (ip, log_entry.on_error))

            except socket.error as exc:
                if not self.terminate_comms:
                    # Report socket errors, but only if we've not told it to terminate_comms.
                    print('[Socket Error]Exception socket.error : %s' % exc)

    def _status_thread(self):
        """ Listen continually to status from the Tellos - should run in its own thread.

            Listens for status messages from each Tello, and saves them in the Tello object as they arrive.
        """

        while not self.terminate_comms:
            try:
                response, ip = self.status_socket.recvfrom(1024)
                response = response.decode()
                if response == 'ok':
                    continue
                ip = ''.join(str(ip[0]))
                tello = self._get_tello(ip)
                tello.status.clear()
                status_parts = response.split(';')
                for status_part in status_parts:
                    key_value = status_part.split(':')
                    if len(key_value) == 2:
                        tello.status[key_value[0]] = key_value[1]

            except socket.error as exc:
                if not self.terminate_comms:
                    # Report socket errors, but only if we've not told it to terminate_comms.
                    print('[Socket Error]Exception socket.error : %s' % exc)
