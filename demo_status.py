from fly_tello import FlyTello
my_tellos = list()


#
# SIMPLE EXAMPLE - MOST BASIC FLIGHT TO SHOW STATUS MESSAGES
#
# SETUP: Any number of Tellos
#


#
# MAIN FLIGHT CONTROL LOGIC
#

# Define the Tello's we're using, in the order we want them numbered
my_tellos.append('0TQDFC6EDBBX03')  # 1-Yellow
my_tellos.append('0TQDFC6EDB4398')  # 2-Blue
# my_tellos.append('0TQDFC6EDBH8M8')  # 3-Green
# my_tellos.append('0TQDFC7EDB4874')  # 4-Red

# Control the flight
with FlyTello(my_tellos, get_status=True) as fly:
    fly.print_status(sync=True)
    fly.takeoff()
    fly.print_status(sync=True)
    fly.land()
    fly.print_status(sync=True)
