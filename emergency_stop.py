#
# Quick and basic code for running a standalone "emergency stop" in case of any problems
#
#
#

import socket
import netaddr
import netifaces
import time


#
# FUNCTION DEFINITIONS
#

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


def send_command(command, possible_addr, control_socket, control_port):
    # Send the command to each Tello on each possible_addr
    for ip in possible_addr:
        try:
            print('Sending %s command to drone at %s' % (command, ip))
            control_socket.sendto(command.encode(), (ip, control_port))
        except OSError as oserror:
            print(oserror)
            print('ERROR! Socket failed - terminating!')
            exit()
        time.sleep(0.01)


def initialise(first_ip, last_ip, control_port, possible_addr):

    # Create socket for communication with Tello
    control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket for sending cmd
    control_socket.bind(('', control_port))

    # Get network addresses to search
    subnets, address = _get_subnets()

    # Create a list of possible IP addresses to search
    for subnet, netmask in subnets:
        for ip in netaddr.IPNetwork('%s/%s' % (subnet, netmask)):
            if not (first_ip <= int(str(ip).split('.')[3]) <= last_ip):
                continue
            # Don't add the server's address to the list
            if str(ip) in address:
                continue
            possible_addr.append(str(ip))

    return possible_addr, control_socket


#
# MAIN SCRIPT
#

print('Emergency Stop Application Started!')
first_ip = 51
last_ip = 54
control_port = 8889
control_socket = None
possible_addr = []

while True:
    # Do nothing until we've got a command
    command = input('Emergency Stop?  ' ' or L = Auto-Land  |  S = Stop  |  E = Emergency Cut-Out  |  Q = Quit: ')

    # If not already initalised, initialise the network connection via a UDP socket
    if not control_socket:
        possible_addr, control_socket = initialise(first_ip, last_ip, control_port, possible_addr)
        print('Connection initialised!')

    if command.upper() == ' ':
        send_command('land', possible_addr, control_socket, control_port)
    elif command.upper() == 'L':
        send_command('land', possible_addr, control_socket, control_port)
    elif command.upper() == 'S':
        send_command('stop', possible_addr, control_socket, control_port)
    elif command.upper() == 'E':
        send_command('emergency', possible_addr, control_socket, control_port)
    elif command.upper() == 'Q':
        print('Q(uit) command received - exiting!')
        exit()
    else:
        print('Invalid command - enter space (to land), L(and), S(top), E(mergency), or Q(uit)')

    time.sleep(0.1)
