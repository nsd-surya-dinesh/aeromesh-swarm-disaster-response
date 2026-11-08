# TODO: Drop-in adapter requiring manifest.json verification not yet performed.
# See audit section 7 — DroneConnection class for pymavlink sysid-matched heartbeat.

class DroneConnection:
    def __init__(self, sysid, endpoint):
        self.sysid = sysid
        self.endpoint = endpoint

    def connect(self):
        pass  # TODO: loop recv_match('HEARTBEAT') until msg.get_srcSystem() == self.sysid, 30s deadline (fix F1)

    def wait_gps(self, timeout=10):
        pass  # TODO: poll GPS_RAW_INT.fix_type >= 3, EKF flags (fix F2)

    def arm(self, force=False):
        pass  # TODO: arm ONCE, use ARMING_SKIPCHK bitmask; never repeated force-arm (fix F3,F4)

    def set_mode(self, mode="GUIDED"):
        pass

    def takeoff(self, alt_m=10):
        pass  # TODO: if GPS missing, fall back to set_position_target_local_ned_send vz < 0 (fix F2)

    def goto(self, lat, lon, alt_m=10):
        pass

    def velocity(self, vx, vy, vz):
        pass

    def position(self):
        return {"lat": 0, "lon": 0, "alt": 0, "heading": 0}

    def battery(self):
        return (0.0, 0)

    def close(self):
        pass  # TODO: close MAVLink connection before opening next (fix F6)
