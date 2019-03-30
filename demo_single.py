from fly_tello import FlyTello
my_tellos = list()


#
# SIMPLE EXAMPLE - SINGLE TELLO WITH MISSION PAD
#
# SETUP: Tello on Mission Pad, facing in direction of the pad - goes max 50cm left and 100cm forward - takes ~45sec
#

#
# MAIN FLIGHT CONTROL LOGIC
#

# Define the Tello's we're using, in the order we want them numbered
my_tellos.append('0TQDFC6EDBBX03')  # 1-Yellow
# my_tellos.append('0TQDFC6EDB4398')  # 2-Blue
# my_tellos.append('0TQDFC6EDBH8M8')  # 3-Green
# my_tellos.append('0TQDFC7EDB4874')  # 4-Red

# Control the flight
with FlyTello(my_tellos) as fly:
    fly.takeoff()
    fly.forward(dist=50)
    fly.back(dist=50)
    fly.reorient(height=100, pad='m-2')
    fly.left(dist=50)
    fly.flip(direction='right')
    fly.reorient(height=100, pad='m-2')
    fly.curve(x1=50, y1=30, z1=0, x2=100, y2=30, z2=-20, speed=60)
    fly.curve(x1=-50, y1=-30, z1=0, x2=-100, y2=-30, z2=20, speed=60)
    fly.reorient(height=100, pad='m-2')
    fly.rotate_cw(angle=360, tello=1)
    fly.straight_from_pad(x=30, y=0, z=75, speed=100, pad='m-2')
    fly.flip(direction='back')
    fly.reorient(height=50, pad='m-2')
    fly.land()
