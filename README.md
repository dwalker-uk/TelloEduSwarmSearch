Tello Edu: Swarm & Search
-

**The Tello Edu**

After coming across the Tello Edu in Jan 2019, it seemed to offer something very new to the small drone market.  Being designed for education, it had a few key features:
* It had a published, open API allowing it to be easily flown with some very simple code.
* Many of them can join the same WiFi Network, enabling multiple Tellos to fly in a **swarm**.
* It has built-in image recognition for a set of 'Mission Pads' which are supplied with it, enabling improved positioning accuracy and **search** challenges to be performed.

Note that the Tello Edu is different from the original Tello - the two key differences are noted in the following section.

**Background & Motivation**

This project is a replacement library for the Tello Edu, based on the official Python SDK here: https://github.com/TelloSDK/Multi-Tello-Formation

The motivations for creating this new project, rather than simply using or updating the official `Multi-Tello-Formation` project were:
* Python 3 support
* Full support for all Tello Edu functionality
    * This project should work equally well with both original **Tello**, and **Tello Edu**, with a couple of limitations:
    * The original Tello lacks the option to connect it to a WiFi Access Point, and so is limited to a single Tello.
    * The original Tello lacks support for Mission Pads, so any methods using those will only work with a Tello Edu.
* More advanced direct Python flight controls, rather than parsing commands from a text file
* Enabling conditional flight controls, for example using the result of one command to determine the next
* Removing race conditions which could occur when a second command was issued before the prior command was fully processed *(This was the biggest driver for starting a completely new project!)*
* Implementing easy shortcut methods for both the Tello SDK and some aggregate behaviours, e.g. following search patterns
* Making both synchronised and totally independent flight behaviours more intuitive and clear to programme

There are some recommendations at the end of this README about improvements I'd suggest for further development.  I don't plan to continue those developments myself, but welcome others to fork this project to do so.

**Configuration / Setup**

Only two non-standard Python libraries are required - ```netifaces``` and ```netaddr```.  These are available for Windows, Mac and Linux.  Otherwise this project is self-contained.

Out of the box, each Tello and Tello Edu is configured with its own WiFi network, to which you connect in order to control them.  However, the Tello Edu can also be made to connect to any other WiFi Network - a pre-requisite for any swarm behaviour.  Once configured, the Tello Edu will always connect to this WiFi Network, until it is reset (by turning on then holding power button for 5-10secs).

To make a Tello Edu connect to a WiFi Network, connect to the Tello (initially by connecting to its own WiFi network) then run the following:
```
from fly_tello import FlyTello
with FlyTello(['XXX']) as fly:
    fly.set_ap_wifi(ssid='MY_SSID', password='MY_PASSWORD')
```
The above code initialises FlyTello, and then sets the SSID and Password you supply.  You can get the Serial Number for your Tello from a tiny sticker inside the battery compartment, but by using `'XXX'` here FlyTello will print the Serial Number to the Console anyway.  You should usually provide the Serial Number when initialising FlyTello, but it's not essential here because there's only one.

**Project Structure**

There are three key files in the project:
* `fly_tello.py` - The `FlyTello` class is intended to be the only one that a typical user needs to use.  It contains functions enabling all core behaviours of one or more Tellos, including some complex behaviour such as searching for Mission Pads.  This should always be the starting point.
* `comms_manager.py` - The `CommsManager` class performs all of the core functions that communicate with the Tellos, sending and receiving commands and status messages, and ensuring they are acted on appropriately.  If you want to develop new non-standard behaviours, you'll probably need some of these functions.
* `tello.py` - The `Tello` class stores key parameters for each Tello, enabling the rest of the functionality.  The `TelloCommand` class provides the structure for both queued commands, and logs of commands which have already been sent.

**FlyTello**

Using `FlyTello` provides the easiest route to flying one or more Tellos.  A simple demonstration would require the following code:
```
from fly_tello import FlyTello      # Import FlyTello

my_tellos = list()
my_tellos.append('0TQDFCAABBCCDD')  # Replace with your Tello Serial Number
my_tellos.append('0TQDFCAABBCCEE')  # Replace with your Tello Serial Number

with FlyTello(my_tellos) as fly:    # Use FlyTello as a Context Manager to ensure safe landing in case of any errors
    fly.takeoff()                   # Single command for all Tellos to take-off
    fly.forward(50)                 # Single command for all Tellos to fly forward by 50cm
    with fly.sync_these():          # Keep the following commands in-sync, even with different commands for each Tello
        fly.left(30, tello=1)       # Tell just Tello1 to fly left
        fly.right(30, tello=2)      # At the same time, Tello2 will fly right
    fly.flip(direction='forward')   # Flips are easy to perform via the Tello SDK
    fly.land()                      # Finally, land
```

It is suggested to browse through `fly_tello.py` for full details of the available methods which you can use - all are fully commented and explained in the code.  A few worth mentioning however include:
* Every function listed in the Tello SDK v2.0 (available to download from https://www.ryzerobotics.com/tello-edu/downloads) is implemented as a method within FlyTello; though some have been renamed for clarity.
* `reorient()` - a simplified method which causes the Tello to centre itself over the selected (or any nearby) Mission Pad.  This is really helpful for long-running flights to ensure the Tellos remain exactly in the right positions.
* `search_spiral()` - brings together multiple Tello SDK commands to effectively perform a search for a Mission Pad, via one very simple Python command.  It will stop over the top of the Mission Pad if it finds it, otherwise returns to its starting position.
* `search_pattern()` - like search_spiral, but you can specify any pattern you like for the search via a simple list of coordinates.
* `sync_these()` - when used as a Context Manager (as a `with` block), this ensures all Tellos are in sync before any functions within the block are executed.

`FlyTello` also provides a simple method of programming individual behaviours, which allow each Tello to behave and follow its own independent set of instructions completely independently from any other Tello.  For full details read the comments in `fly_tello.py`, but key extracts from an example of this are also shown below:
```
# independent() is used to package up the FlyTello commands for the independent phase of the flight
def independent(tello, pad):
    found = fly.search_spiral(dist=50, spirals=2, height=100, speed=100, pad=pad, tello=tello)
    if found:
        print('[Search]Tello %d Found the Mission Pad!' % tello)
        fly.land(tello=tello)

with FlyTello(my_tellos) as fly:
    with fly.individual_behaviours():
        # individual_behaviours() is a Context Manager to ensure separate threads are setup and managed for each Tello's
        # own behaviour, as defined in the independent() function above.
        # run_individual() actually initiates the behaviour for a single Tello - in this case both searching, but each
        # is searching for a different Mission Pad ('m1' vs 'm2').
        fly.run_individual(independent, tello_num=1, pad_id='m1')
        fly.run_individual(independent, tello_num=2, pad_id='m2')
```

**Demos**

Two demo videos are provided on YouTube, showing the capabilities of Tello Edu with this library.
* Tello Edu Capabilities Demo (`demo_all_functions.py`) - https://youtu.be/F3rSW5VKsW8
* Simple Searching Demo (`demo_search.py`) - https://youtu.be/pj2fJe7cPTE

**Limitations**

There are some limitations of what can be done with this project and the Tello Edu:
* No Video Stream.  The Tello is capable of sending its video stream, but only when connected directly to the in-build WiFi of a single Tello.  The video is not accessible when the Tellos are connected to a separate WiFi network, as required for swarming behaviour.  There is a workaround, which is to have multiple WiFi dongles connected to a single computer, one per Tello, but that hasn't been a focus for me.
* Limited Status Messages.  The Tello does broadcast a regular (multiple times per second) status message, however this seems to be of limited value as many of the values do not seem to correspond with the Tello's behaviour, and others are rather erratic.  This requires further investigation to determine which are useful.

**Recommendations**

The project as it is currently is enough to fly one or more Tello Edu drones via a simple yet sophisticated set of controls.  Expanding its capabilities is easy, with layers of modules which expose increasingly more detailed / low-level functionality.  I'd suggest adding or changing:
* Position Tracking.  By tracking the relative position of each Tello from when it launches, this will enable behaviours such as "return to start", and will e.g. allow Mission Pad locations to be shared with other Tellos in the swarm - a pre-requisite for collaborative swarm behaviour.  Clearly accuracy will decrease over time, but could be regularly restored using the `reorient()` method described above.
* Better Error Checking.  Some error checking is already implemented, but it's incomplete.  Getting the arc radius correct for a curve is sometimes difficult, and this project could be more helpful in identifying the errors and suggesting valid alternative values.
* Implement `on_error` alternative commands for Flips and Curves, which can easily fail due to e.g. battery low or incorrect curve radius values.  This will ensure Tello is less likely to end up in an unexpected location.
* Command Stream & Logging.  Currently all commands either sent or received are printed to the Python Console.  These would be better saved in a detailed log file, so that only key information is presented to the user in the Console.

