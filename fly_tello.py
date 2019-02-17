import time
import threading
from typing import Union, Optional
from contextlib import contextmanager
from comms_manager import CommsManager


class FlyTello:
    """ Abstract class providing a simpler, user-friendly interface to CommsManager and Tello classes.

        FlyTello is dependent on CommsManager, which itself uses Tello and TelloCommand.

        FlyTello is intended to be used as a Context Manager, i.e. to be initialised using a "with" statement, e.g.:
            with FlyTello([sn1, sn2]) as fly:
                fly.takeoff()
    """

    #
    # CLASS INITIALISATION AND CONTEXT HANDLER
    #

    def __init__(self, tello_sn_list: list, get_status=False, first_ip: int=1, last_ip: int=254):
        """ Initiate FlyTello, starting up CommsManager, finding and initialising our Tellos, and reporting battery.

            :param tello_sn_list: List of serial numbers, in the order we want to number the Tellos.
            :param first_ip: Optionally, we can specify a smaller range of IP addresses to speed up the search.
            :param last_ip: Optionally, we can specify a smaller range of IP addresses to speed up the search.
        """
        self.tello_mgr = CommsManager()
        self.tello_mgr.init_tellos(sn_list=tello_sn_list, get_status=get_status, first_ip=first_ip, last_ip=last_ip)
        self.tello_mgr.queue_command('battery?', 'Read', 'All')
        self.individual_behaviour_threads = []
        self.in_sync_these = False

    def __enter__(self):
        """ (ContextManager) Called when FlyTello is initiated using a with statement. """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ (ContextManager) Tidies up when FlyTello leaves the scope of its with statement. """
        if exc_type is not None:
            # If leaving after an Exception, ensure all Tellos have landed...
            self.tello_mgr.queue_command('land', 'Control', 'All')
            print('[Exception Occurred]All Tellos Landing...')
        else:
            pass
        # In all cases, wait until all commands have been sent and responses received before closing comms and exiting.
        self.tello_mgr.wait_sync()
        self.tello_mgr.close_connections()

    #
    # TELLO SDK V2.0 COMMANDS: CONTROL
    #
    # Control commands perform validation of input parameters.  tello_num can be an individual (1,2,...) or 'All'.
    # If sync is True, will wait until all Tellos are ready before executing command.
    #   Note sync is ignored (i.e. False) if tello_num is 'All', or if is called within a sync_these 'with' block.
    #

    def takeoff(self, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Auto takeoff, ascends to ~50cm above the floor. """
        self._command('takeoff', 'Control', tello, sync)

    def land(self, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Auto landing """
        self._command('land', 'Control', tello, sync)

    def stop(self, tello: Union[int, str]='All') -> None:
        """ Stop Tello wherever it is, even if mid-manoeuvre. """
        self._command('stop', 'Control', tello, sync=False)

    def emergency(self, tello: Union[int, str]='All') -> None:
        """ Immediately kill power to the Tello's motors. """
        self._command('emergency', 'Control', tello, sync=False)

    def up(self, dist: int, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Move up by dist (in cm) """
        self._command_with_value('up', 'Control', dist, 20, 500, 'cm', tello, sync)

    def down(self, dist: int, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Move down by dist (in cm) """
        self._command_with_value('down', 'Control', dist, 20, 500, 'cm', tello, sync)

    def left(self, dist: int, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Move left by dist (in cm) """
        self._command_with_value('left', 'Control', dist, 20, 500, 'cm', tello, sync)

    def right(self, dist: int, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Move right by dist (in cm) """
        self._command_with_value('right', 'Control', dist, 20, 500, 'cm', tello, sync)

    def forward(self, dist: int, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Move forward by dist (in cm) """
        self._command_with_value('forward', 'Control', dist, 20, 500, 'cm', tello, sync)

    def back(self, dist: int, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Move back by dist (in cm) """
        self._command_with_value('back', 'Control', dist, 20, 500, 'cm', tello, sync)

    def rotate_cw(self, angle: int, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Rotate clockwise (turn right) by angle (in degrees) """
        self._command_with_value('cw', 'Control', angle, 1, 360, 'degrees', tello, sync)

    def rotate_ccw(self, angle: int, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Rotate anti-clockwise (turn left) by angle (in degrees) """
        self._command_with_value('ccw', 'Control', angle, 1, 360, 'degrees', tello, sync)

    def flip(self, direction: str, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Perform a flip in the specified direction (left/right/forward/back) - will jump ~30cm in that direction.

            Note that Tello is unable to flip if battery is less than 50%!
        """
        # TODO: Add an on_error command, which moves the Tello in the direction of the flip should the flip fail, e.g.
        # TODO:  if the battery is low.  Will ensure Tello is still in the expected position afterwards.
        # Convert left/right/forward/back direction inputs into the single letters (l/r/f/b) used by the Tello SDK.
        dir_dict = {'left': 'l', 'right': 'r', 'forward': 'f', 'back': 'b'}
        self._command_with_options('flip', 'Control', dir_dict[direction], ['l', 'r', 'f', 'b'], tello, sync)

    def straight(self, x: int, y: int, z: int, speed: int, tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Fly straight to the coordinates specified, relative to the current position.

            :param x: x offset (+ forward, - back) in cm
            :param y: y offset (+ left, - right) in cm
            :param z: z offset (+ up, - down) in cm
            :param speed: Speed (in range 10-100cm/s)
            :param tello: The number of an individual Tello (1,2,...), or 'All'.
            :param sync: If True, will wait until all Tellos are ready before executing the command.
        """
        self._control_multi(command='go',
                            val_params=[(x, -500, 500, 'x'),
                                        (y, -500, 500, 'y'),
                                        (z, -500, 500, 'z'),
                                        (speed, 10, 100, 'speed')],
                            opt_params=[], tello_num=tello, sync=sync)

    def curve(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int,
              tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Fly a curve from current position, passing through mid point on way to end point (relative to current pos).

            The curve will be defined as an arc which passes through the three points (current, mid and end).  The arc
            must have a radius between 50-1000cm (0.5-10m), otherwise the Tello will not move.  Note that validation
            does *not* check the curve radius.

            :param x1: x offset of mid point of the curve (+ forward, - back) in cm
            :param y1: y offset of mid point of the curve (+ left, - right) in cm
            :param z1: z offset of mid point of the curve (+ up, - down) in cm
            :param x2: x offset of end point of the curve (+ forward, - back) in cm
            :param y2: y offset of end point of the curve (+ left, - right) in cm
            :param z2: z offset of end point of the curve (+ up, - down) in cm
            :param speed: Speed (in range 10-60cm/s)  *** Note lower max speed of 60cm/s in curves ***
            :param tello: The number of an individual Tello (1,2,...), or 'All'.
            :param sync: If True, will wait until all Tellos are ready before executing the command.
        """
        # TODO: Add an on_error command, which still moves the Tello to its destination should the curve fail, e.g.
        # TODO:  if the curve radius is invalid.  Will ensure Tello is still in the expected position afterwards.
        self._control_multi(command='curve',
                            val_params=[(x1, -500, 500, 'x1'),
                                        (y1, -500, 500, 'y1'),
                                        (z1, -500, 500, 'z1'),
                                        (x2, -500, 500, 'x2'),
                                        (y2, -500, 500, 'y2'),
                                        (z2, -500, 500, 'z2'),
                                        (speed, 10, 60, 'speed')],
                            opt_params=[], tello_num=tello, sync=sync)

    def straight_from_pad(self, x: int, y: int, z: int, speed: int, pad: str,
                          tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Fly straight to the coordinates specified, relative to the orientation of the mission pad.

            If the mission pad cannot be found, the Tello will not move, except to go to the height (z) above the pad.
            The Tello will always move to a position relative to the pad itself; not relative to the Tello's current
            position.  This means that even if a Tello is slightly offset from the pad, it will always fly to the
            same location relative to the pad, i.e. helps to realign the Tello's location from that reference point.

            :param x: x offset from pad (+ forward, - back) in cm
            :param y: y offset from pad (+ left, - right) in cm
            :param z: z offset from pad (+ up, - down) in cm
            :param speed: Speed (in range 10-100cm/s)
            :param pad: ID of the mission pad to search for, e.g. 'm1'-'m8', 'm-1' (random pad), or 'm-2' (nearest pad).
            :param tello: The number of an individual Tello (1,2,...), or 'All'.
            :param sync: If True, will wait until all Tellos are ready before executing the command.
        """
        self._control_multi(command='go',
                            val_params=[(x, -500, 500, 'x'),
                                        (y, -500, 500, 'y'),
                                        (z, -500, 500, 'z'),
                                        (speed, 10, 100, 'speed')],
                            opt_params=[(pad, ['m1', 'm2', 'm3', 'm4', 'm5',
                                               'm6', 'm7', 'm8', 'm-1', 'm-2'], 'mid')],
                            tello_num=tello, sync=sync)

    def curve_from_pad(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int, pad: str,
                       tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Fly a curve from current position, passing through mid point on way to end point (relative to mission pad).

            If the mission pad cannot be found, the Tello will not move, except to go to the height (z) above the pad.
            The curve will be defined as an arc which passes through three points - directly above pad, mid, and end.
            The arc must have a radius between 50-1000cm (0.5-10m), otherwise the Tello will not move.  Because the
            position is relative to the pad, rather than the Tello itself, the curve radius can change depending on how
            near to the pad the Tello starts.  Note that validation does *not* check the curve radius.

            :param x1: x offset from pad of mid point of the curve (+ forward, - back) in cm
            :param y1: y offset from pad of mid point of the curve (+ left, - right) in cm
            :param z1: z offset from pad of mid point of the curve (+ up, - down) in cm
            :param x2: x offset from pad of end point of the curve (+ forward, - back) in cm
            :param y2: y offset from pad of end point of the curve (+ left, - right) in cm
            :param z2: z offset from pad of end point of the curve (+ up, - down) in cm
            :param speed: Speed (in range 10-60cm/s)  *** Note lower max speed of 60cm/s in curves ***
            :param pad: ID of the mission pad to search for, e.g. 'm1'-'m8', 'm-1' (random pad), or 'm-2' (nearest pad).
            :param tello: The number of an individual Tello (1,2,...), or 'All'.
            :param sync: If True, will wait until all Tellos are ready before executing the command.
        """
        # TODO: Add an on_error command, which still moves the Tello to its destination should the curve fail, e.g.
        # TODO:  if the curve radius is invalid.  Will ensure Tello is still in the expected position afterwards.
        self._control_multi(command='curve',
                            val_params=[(x1, -500, 500, 'x1'),
                                        (y1, -500, 500, 'y1'),
                                        (z1, -500, 500, 'z1'),
                                        (x2, -500, 500, 'x2'),
                                        (y2, -500, 500, 'y2'),
                                        (z2, -500, 500, 'z2'),
                                        (speed, 10, 60, 'speed')],
                            opt_params=[(pad, ['m1', 'm2', 'm3', 'm4', 'm5',
                                               'm6', 'm7', 'm8', 'm-1', 'm-2'], 'mid')],
                            tello_num=tello, sync=sync)

    def jump_between_pads(self, x: int, y: int, z: int, speed: int, yaw: int, pad1: str, pad2: str,
                          tello: Union[int, str]='All', sync: bool=True) -> None:
        """ Fly straight from pad1 to the coordinates specified (relative to pad1), then find pad2 at the end point.

            If the first mission pad cannot be found, the Tello will not move, except to go to the height (z) above the
            first pad.  If the second mission pad cannot be found, the Tello will have moved to the point relative to
            pad1, but will return an error.

            :param x: x offset from pad1 (+ forward, - back) in cm
            :param y: y offset from pad1 (+ left, - right) in cm
            :param z: z offset from pad1 (+ up, - down) in cm
            :param speed: Speed (in range 10-100cm/s)
            :param yaw: Angle to rotate to, relative to the mission pad's orientation (direction that rocket points)
            :param pad1: ID of the mission pad at start, e.g. 'm1'-'m8', 'm-1' (random pad), or 'm-2' (nearest pad).
            :param pad2: ID of the mission pad at end, e.g. 'm1'-'m8', 'm-1' (random pad), or 'm-2' (nearest pad).
            :param tello: The number of an individual Tello (1,2,...), or 'All'.
            :param sync: If True, will wait until all Tellos are ready before executing the command.
        """
        self._control_multi(command='jump',
                            val_params=[(x, -500, 500, 'x'),
                                        (y, -500, 500, 'y'),
                                        (z, -500, 500, 'z'),
                                        (speed, 10, 100, 'speed'),
                                        (yaw, 0, 360, 'yaw')],
                            opt_params=[(pad1, ['m1', 'm2', 'm3', 'm4', 'm5',
                                                'm6', 'm7', 'm8', 'm-1', 'm-2'], 'mid1'),
                                        (pad2, ['m1', 'm2', 'm3', 'm4', 'm5',
                                                'm6', 'm7', 'm8', 'm-1', 'm-2'], 'mid2')],
                            tello_num=tello, sync=sync)

    #
    # TELLO SDK V2.0 COMMANDS: SET
    #

    def set_speed(self, speed: int, tello: Union[int, str]='All', sync: bool=False) -> None:
        """ Set 'normal' max speed for the Tello, for e.g. 'forward', 'back', etc commands. """
        self._command_with_value('speed', 'Set', speed, 10, 100, 'cm/s', tello, sync)

    def set_rc(self, left_right: int, forward_back: int, up_down: int, yaw: int,
               tello: Union[int, str]='All', sync: bool=False) -> None:
        """ Simulate remote controller commands, with range of -100 to +100 on each axis. """
        self._control_multi(command='rc',
                            val_params=[(left_right, -100, 100, 'left_right'),
                                        (forward_back, -100, 100, 'forward_back'),
                                        (up_down, -100, 100, 'up_down'),
                                        (yaw, -100, 100, 'yaw')],
                            opt_params=[], tello_num=tello, sync=sync)

    def set_own_wifi(self, ssid: str, password: str, tello: int, sync: bool=False) -> None:
        """ Set the Tello's own WiFi built-in hotspot to use the specified name (ssid) and password. """
        self._command('wifi %s %s' % (ssid, password), 'Set', tello, sync)

    def pad_detection_on(self, tello: Union[int, str]='All', sync: bool=False) -> None:
        """ Turn on mission pad detection - must be set before setting direction or using pads.  """
        self._command('mon', 'Set', tello, sync)

    def pad_detection_off(self, tello: Union[int, str]='All', sync: bool=False) -> None:
        """ Turn off mission pad detection - commands using mid will not work if this is off. """
        self._command('moff', 'Set', tello, sync)

    def set_pad_detection(self, direction: str, tello: Union[int, str]='All', sync: bool=False) -> None:
        """ Set the direction of mission pad detection.  Must be done before mission pads are used.

            :param direction: Either 'downward', 'forward', or 'both'.
            :param tello: The number of an individual Tello (1,2,...), or 'All'.
            :param sync: If True, will wait until all Tellos are ready before executing the command.
        """
        # Convert descriptions (downward/forward/both) into 0/1/2 required by Tello SDK.
        dir_dict = {'downward': 0, 'forward': 1, 'both': 2}
        self._command_with_options('mdirection', 'Set', dir_dict[direction], [0, 1, 2], tello, sync)

    def set_ap_wifi(self, ssid: str, password: str, tello: Union[int, str]='All', sync: bool=False) -> None:
        """ Tell the Tello to connect to an existing WiFi network using the supplied ssid and password. """
        self._command('ap %s %s' % (ssid, password), 'Set', tello, sync)

    #
    # TELLO SDK V2.0 COMMANDS: READ
    #
    # Note arguments are common: tello can be an individual or 'All'; sync=True will wait until all are ready.
    #

    def get_speed(self, tello: Union[str, int]='All', sync: bool=False) -> None:
        """ Reads the speed setting of the Tello(s), in range 10-100.  Reflects max speed, not actual current speed. """
        self._command('speed?', 'Read', tello, sync)

    def get_battery(self, tello: Union[str, int]='All', sync: bool=False) -> None:
        """ Read the battery level of the Tello(s) """
        self._command('battery?', 'Read', tello, sync)

    def get_time(self, tello: Union[str, int]='All', sync: bool=False) -> None:
        """ Should get current flight time of the Tello(s) """
        self._command('time?', 'Read', tello, sync)

    def get_wifi(self, tello: Union[str, int]='All', sync: bool=False) -> None:
        """ Should get WiFi signal-to-noise ratio (SNR) - doesn't appear very reliable """
        self._command('wifi?', 'Read', tello, sync)

    def get_sdk(self, tello: Union[str, int]='All', sync: bool=False) -> None:
        """ Read the SDK version of the Tello(s) """
        self._command('sdk?', 'Read', tello, sync)

    def get_sn(self, tello: Union[str, int]='All', sync: bool=False) -> None:
        """ Read the Serial Number of the Tello(s) """
        self._command('sn?', 'Read', tello, sync)

    #
    # TELLO SDK V2.0 EXTENDED & COMPOSITE COMMANDS
    #

    def reorient(self, height: int, pad: str, tello: Union[str, int]='All', sync: bool=False) -> None:
        """ Shortcut method to re-centre the Tello on the specified pad, helping maintain accurate positioning.

            Whilst the Tello has fairly good positioning stability by default, they can drift after flying for some
            time, or performing several manoeuvres.  Using reorient gets back to a known position over a mission pad.

            :param height: Height above pad to fly to.
            :param pad: ID of the mission pad to reorient over, e.g. 'm1'-'m8', 'm-1', or 'm-2'.
            :param tello: The number of an individual Tello (1,2,...), or 'All'.
            :param sync: If True, will wait until all Tellos are ready before executing the command.
        """
        self._control_multi(command='go',
                            val_params=[(0, -500, 500, 'x'),
                                        (0, -500, 500, 'y'),
                                        (height, -500, 500, 'z'),
                                        (100, 10, 100, 'speed')],
                            opt_params=[(pad, ['m1', 'm2', 'm3', 'm4', 'm5',
                                               'm6', 'm7', 'm8', 'm-1', 'm-2'], 'mid')],
                            tello_num=tello,
                            sync=sync)

    def search_spiral(self, dist: int, spirals: int, height: int, speed: int, pad: str, tello: int) -> bool:
        """ Shortcut method to perform a spiral search around the starting point, returning True when found.

            Search follows a square pattern around, enlarging after each complete revolution.  If pad is not found
            by the end of the last spiral, Tello will move back to its starting point and this method returns False.

            :param dist: Distance (in cm) from centre point to extend the spiral each time.
            :param spirals: Number of spirals to complete, moving out by 'dist' each time.  Currently max 3.
            :param height: Height (cm) above ground at which to fly when searching.  Detection range is 30-120cm.
            :param speed: Flight speed, in range 10-100cm/s.
            :param pad: ID of the mission pad to search for, e.g. 'm1'-'m8', 'm-1', or 'm-2'.
            :param tello: Number of an individual Tello, i.e. 1,2,....  Doesn't support 'All'.
            :return: Returns True when mission pad is found, and Tello is hovering directly above it.  Otherwise False.
        """
        pattern = []
        if spirals >= 1:
            pattern.extend([(1, 1),
                            (0, -2),
                            (-2, 0),
                            (0, 2)])

        if spirals == 1:
            # Return to starting location
            pattern.extend([(1, -1)])
        elif spirals >= 2:
            pattern.extend([(1, 1),
                            (2, 0),
                            (0, -2),
                            (0, -2),
                            (-2, 0),
                            (-2, 0),
                            (0, 2),
                            (0, 2)])

        if spirals == 2:
            # Return to starting location
            pattern.extend([(2, -2)])
        elif spirals >= 3:
            pattern.extend([(1, 1),
                            (2, 0),
                            (2, 0),
                            (0, -2),
                            (0, -2),
                            (0, -2),
                            (-2, 0),
                            (-2, 0),
                            (-2, 0),
                            (0, 2),
                            (0, 2),
                            (0, 2)])

        if spirals >= 3:
            # Return to starting location
            pattern.extend([(3, -3)])

        return self.search_pattern(pattern, dist, height, speed, pad, tello)

    def search_pattern(self, pattern: list, dist: int, height: int, speed: int, pad: str, tello: int) -> bool:
        """ Perform a search for a mission pad by following the supplied pattern, returning True when found.

            Pattern is usually clearest to define using relative integers, e.g. (0, 2), (-1, -1), etc.  pattern_dist
            is therefore provided which is applied as a multiplier to all pattern values.  If not needed then set to 1.

            :param pattern: A list of (x, y) tuples, defining the movement for each step of the search.
            :param dist: Multiplier for pattern values - if pattern has correct distances, set this to 1.
            :param height: Height (cm) above ground at which to fly when searching.  Detection range is 30-120cm.
            :param speed: Flight speed, in range 10-100cm/s.
            :param pad: ID of the mission pad to search for, e.g. 'm1'-'m8', 'm-1', or 'm-2'.
            :param tello: Number of an individual Tello, i.e. 1,2,....  Doesn't support 'All'.
            :return: Returns True when mission pad is found, and Tello is hovering directly above it.  Otherwise False.
        """
        for x in range(0, len(pattern)):
            # Try to centre over the nearest mission pad
            cmd_ids = self.tello_mgr.queue_command('go 0 0 %d %d %s' % (height, speed, pad),
                                                   'Control', tello)
            for cmd_id in cmd_ids:
                cmd_log = self.tello_mgr.get_tello(cmd_id[0]).log_wait_response(cmd_id[1])
                if cmd_log.success:
                    return True
                else:
                    # If not found i.e. Tello unable to orient itself over the Mission Pad, move to next position...
                    self.tello_mgr.queue_command('go %d %d %d %d' % (pattern[x][0] * dist,
                                                                     pattern[x][1] * dist, 0, speed),
                                                 'Control', tello)
        return False

    #
    # MULTI-THREADING CONTROL FOR INDIVIDUAL BEHAVIOURS
    #

    @contextmanager
    def individual_behaviours(self):
        """ Context Manager, within which each Tello can have individual behaviours running in their own threads.

            By using this context manager, the individual threads will be monitored and the main thread will be blocked
            until all individual behaviours have completed.  This allows individual behaviours to happen at some points
            in the flight control logic, but for Tellos to re-sync once they've completed their individual behaviour.
        """
        # Clear list used to keep track of threads
        self.individual_behaviour_threads.clear()
        # Yield to allow threads to be created, inside the with statement
        yield
        # Block at the end of the with statement until all threads have completed
        for thread in self.individual_behaviour_threads:
            thread.join()

    def run_individual(self, behaviour, **kwargs):
        """ Start individual behaviour in its own thread, passing on keyword arguments to the behaviour function.

            Keeps main flight logic clear and simple, hiding threading capability within here.  Should be run within
            the individual_behaviours() Context Manager to ensure threads are managed appropriately.

            :param behaviour: A (usually) custom-written function, to perform specific behaviour.
            :param kwargs: Any keyword arguments, i.e. arg_name1=value1, arg_name2=value2, etc, for the above function.
        """
        thread = threading.Thread(target=behaviour, kwargs=kwargs)
        thread.start()
        self.individual_behaviour_threads.append(thread)

    #
    # SYNC AND TIMING METHODS
    #

    def wait_sync(self) -> None:
        """ Block execution until all Tellos are ready, i.e. no queued commands or pending responses. """
        self.tello_mgr.wait_sync()

    @contextmanager
    def sync_these(self) -> None:
        """ Synchronise the commands within the "with" block, when this is used as a Context Manager.

            Provides a clearer way to layout code which will ensure all Tellos are ready before the code within this
            block will execute.  Equivalent to calling wait_sync() prior to the same commands.

            sync_these() is intended to be used as a Context Manager, i.e. to initialise using a "with" statement, e.g.:
                with fly.sync_these():
                    fly.left(50, 1)
                    fly.right(50, 2)
            Note that any sync=True setting on commands inside the block will be ignored!
        """
        self.tello_mgr.wait_sync()
        self.in_sync_these = True
        yield
        self.in_sync_these = False

    @staticmethod
    def pause(secs: float) -> None:
        """ Pause for specified number of seconds, then continue.

            :param secs: Number of seconds to pause by.  Can be integer or floating point i.e. 1, 0.1, etc
        """
        time.sleep(secs)

    def flight_complete(self, tello: int) -> None:
        """ Mark the Tello's flight as complete - will ignore any subsequent control commands.
        
            :param tello: Tello Number - must be a single Tello, referenced by its number.  Cannot be 'All'.
        """
        self.tello_mgr.get_tello(tello).flight_complete = True

    #
    # STATUS MESSAGE PROCESSING
    #

    def print_status(self, tello: Union[int, str]='All', sync: bool=False) -> None:
        """ Print the entire Status Message to the Python Console, for the specified Tello(s). """
        if sync and not self.in_sync_these:
            self.tello_mgr.wait_sync()
        if tello == 'All':
            for tello in self.tello_mgr.tellos:
                print('Tello %d Status: %s' % (tello.num, tello.status))
        else:
            tello = self.tello_mgr.get_tello(num=tello)
            print('Tello %d Status: %s' % (tello.num, tello.status))

    def get_status(self, key: str, tello: int, sync: bool=False) -> Optional[str]:
        """ Return the value of a specific key from an individual Tello  """
        if sync and not self.in_sync_these:
            self.tello_mgr.wait_sync()
        tello = self.tello_mgr.get_tello(num=tello)
        if key in tello.status:
            return tello.status[key]
        return None

    #
    # PRIVATE SHORTCUT METHODS
    #

    def _command(self, command, command_type, tello_num, sync):
        if sync and tello_num == 'All' and not self.in_sync_these:
            # TODO: Review whether tello_num=='All' should preclude wait_sync - might want to keep it!
            self.tello_mgr.wait_sync()
        self.tello_mgr.queue_command(command, command_type, tello_num)

    def _command_with_value(self, command, command_type, value, val_min, val_max, units, tello_num, sync):
        if sync and tello_num == 'All' and not self.in_sync_these:
            self.tello_mgr.wait_sync()
        if val_min <= value <= val_max:
            self.tello_mgr.queue_command('%s %d' % (command, value), command_type, tello_num)
        else:
            print('[FlyTello Error]%s %d - value must be %d-%d%s.' % (command, value, val_min, val_max, units))

    def _command_with_options(self, command, command_type, option, validate_options, tello_num, sync):
        # TODO: Allow an on_error value to be passed through to queue_command
        if sync and tello_num == 'All' and not self.in_sync_these:
            self.tello_mgr.wait_sync()
        if option in validate_options:
            self.tello_mgr.queue_command('%s %s' % (command, option), command_type, tello_num)
        else:
            print('[FlyTello Error]%s %s - value must be in list %s.' % (command, option, validate_options))

    def _control_multi(self, command: str, val_params: list, opt_params: list, tello_num: Union[int, str], sync: bool):
        """ Shortcut method to validate and send commands to Tello(s).

            Can have value parameters, option parameters, or both.  These will always be applied in the order supplied,
            so must exactly match what is expected (as defined in the Tello SDK).  Validation is not necessarily
            comprehensive, i.e. currently doesn't check for curve radius, or where x, y and z are all < 20.

            :param command: Base command in text format, from the Tello SDK.
            :param val_params: List of tuples, in the form: [(value, validate_min, validate_max, label), (...), ...]
            :param opt_params: List of tuples, in the form: [(value, validate_list, label), (...), ...]
            :param tello_num: Can be an individual Tello num (1,2,...), or 'All'.
            :param sync: Only valid if tello_num is 'All' - waits until all Tellos ready before sending the command.
            :return: Returns list of cmd_ids, from queue_command() - or nothing
        """
        # TODO: Allow an on_error value to be passed through to queue_command
        if sync and tello_num == 'All' and not self.in_sync_these:
            self.tello_mgr.wait_sync()

        command_parameters = ''

        for val_param in val_params:
            if val_param[1] <= val_param[0] <= val_param[2]:
                command_parameters = '%s %d' % (command_parameters, val_param[0])
            else:
                print('[FlyTello Error]%s - %s parameter out-of-range.' % (command, val_param[3]))
                return

        for opt_param in opt_params:
            if opt_param[0] in opt_param[1]:
                command_parameters = '%s %s' % (command_parameters, opt_param[0])
            else:
                print('[FlyTello Error]%s - %s parameter not valid.' % (command, opt_param[2]))
                return

        self.tello_mgr.queue_command('%s%s' % (command, command_parameters), 'Control', tello_num)
