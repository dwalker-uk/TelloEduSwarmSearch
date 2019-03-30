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
my_tellos.append('0TQDFC6EDBBX03')  # 1-Yellow
my_tellos.append('0TQDFC6EDB4398')  # 2-Blue
# my_tellos.append('0TQDFC6EDBH8M8')  # 3-Green
# my_tellos.append('0TQDFC7EDB4874')  # 4-Red

# Control the flight
with FlyTello(my_tellos) as fly:
    fly.takeoff()
    fly.forward(dist=50)
    fly.back(dist=50)
    fly.reorient(height=100, pad='m-2')
    with fly.sync_these():
        fly.left(dist=50, tello=1)
        fly.right(dist=50, tello=2)
    with fly.sync_these():
        fly.flip(direction='right', tello=1)
        fly.flip(direction='left', tello=2)
    fly.reorient(height=100, pad='m-2')
    fly.straight(x=75, y=75, z=0, speed=100)
    fly.curve(x1=-55, y1=-20, z1=0, x2=-75, y2=-75, z2=0, speed=60)
    with fly.sync_these():
        fly.rotate_cw(angle=360, tello=1)
        fly.rotate_ccw(angle=360, tello=2)
    fly.straight_from_pad(x=50, y=0, z=75, speed=100, pad='m-2')
    fly.flip(direction='back')
    fly.reorient(height=50, pad='m-2')
    fly.land()
