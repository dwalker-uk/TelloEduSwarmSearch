from fly_tello import FlyTello
my_tellos = list()


#
# SIMPLE EXAMPLE - TWO TELLOs INDEPENDENTLY SEARCHING FOR MISSION PADS, IN AN OUTWARD SPIRAL PATTERN.
#
# PHYSICAL SETUP: Two Tellos back to back, ~30-50cm apart, with mission pads scattered roughly around.
#


#
# INDIVIDUAL BEHAVIOURAL FUNCTIONS
#

def threaded_search_test(tello, pad_id):
    """ This function defines Tello behaviour for the search itself, when each Tello is searching independently. """
    found = fly.search_spiral(dist=50, spirals=2, height=100, speed=100, pad=pad_id, tello=tello)
    if found:
        print('[Search]Tello %d Found the Mission Pad!' % tello)
        # Hover at low-level directly over the pad, to make an accurate landing
        fly.reorient(height=40, pad=pad_id, tello=tello, sync=False)
        fly.land(tello=tello)
        fly.flight_complete(tello=tello)


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
    fly.pad_detection_on()
    fly.set_pad_detection(direction='downward')
    fly.takeoff()
    with fly.individual_behaviours():
        # Tellos will each fly independently, as defined in the function above.  If they find their own mission pad they
        #  will land and ignore any later commands.  Otherwise, they will continue after the with statement ends.
        fly.run_individual(threaded_search_test, tello_num=1, pad_id='m1')
        fly.run_individual(threaded_search_test, tello_num=2, pad_id='m2')
    fly.land()
