from fly_tello import FlyTello
my_tellos = list()


#
# SIMPLE EXAMPLE - TWO TELLOs FLYING IN SYNC, DEMO'ING ALL KEY TELLO CAPABILITIES
#
# SETUP: Tello both facing away from controller, first Tello on the left, approx 0.5-1m apart
#


#
# MAIN FLIGHT CONTROL LOGIC
#

# Define the Tello's we're using, in the order we want them numbered
my_tellos.append('0TQDFC6EDBBX03')
my_tellos.append('0TQDFC6EDB4398')

# Control the flight
with FlyTello(my_tellos) as fly:
    fly.takeoff()
    fly.forward(50)
    fly.back(50)
    fly.reorient_on_pad(100, 'm-2')
    with fly.sync_these():
        fly.left(50, 1)
        fly.right(50, 2)
    with fly.sync_these():
        fly.flip('right', 1)
        fly.flip('left', 2)
    fly.reorient_on_pad(100, 'm-2')
    fly.straight(75, 75, 0, 100)
    fly.curve(-55, -20, 0, -75, -75, 0, 60)
    with fly.sync_these():
        fly.rotate_cw(360, 1)
        fly.rotate_ccw(360, 2)
    fly.straight_from_pad(50, 0, 75, 100, 'm-2')
    fly.flip('back')
    fly.reorient_on_pad(50, 'm-2')
    fly.land()
