"""
Vehicle State Interface for AeroMesh-Swarm

Provides a hardware-independent representation of UAV telemetry and health.
All units and coordinate frames are explicit. Used by the Command Validation
Safety Layer and Mission Planner to make decisions based on fresh, validated state.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import time
import math


class CoordinateFrame(Enum):
    """Explicit coordinate frame enumeration"""
    NED_LOCAL = "ned_local"           # North-East-Down local tangent frame (meters, origin at home/GCS)
    WGS84_GPS = "wgs84_gps"           # WGS84 latitude/longitude/altitude (degrees, degrees, meters MSL)
    ENU_LOCAL = "enu_local"           # East-North-Up local tangent frame (meters)
    BODY_FRD = "body_frd"             # Body Forward-Right-Down frame (meters)


class FlightMode(Enum):
    """Standardized flight modes across autopilots"""
    MANUAL = "manual"
    STABILIZE = "stabilize"
    ALTITUDE_HOLD = "altitude_hold"
    POSITION_HOLD = "position_hold"
    LOITER = "loiter"
    AUTO = "auto"
    GUIDED = "guided"
    RTL = "rtl"                       # Return to Launch
    LAND = "land"
    TAKEOFF = "takeoff"
    FAILSAFE = "failsafe"
    UNKNOWN = "unknown"


class VehicleHealth(Enum):
    """Vehicle health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"             # Some sensors/systems degraded but flyable
    CRITICAL = "critical"             # Unsafe to continue; failsafe should trigger
    FAILSAFE = "failsafe"             # Autopilot failsafe active
    UNKNOWN = "unknown"


@dataclass
class VehicleTelemetry:
    """
    Timestamped vehicle telemetry snapshot.

    All positions/velocities are in NED_LOCAL frame unless otherwise noted.
    Coordinate frame of position/velocity MUST be specified via frame field.
    """
    vehicle_id: int
    timestamp: float                  # Monotonic time (seconds) when telemetry was received

    # Position (frame-specific)
    position: tuple[float, float, float]  # (x, y, z) in specified frame
    velocity: tuple[float, float, float]  # (vx, vy, vz) in specified frame
    frame: CoordinateFrame = CoordinateFrame.NED_LOCAL

    # Attitude (body frame, radians)
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    # Battery
    battery_voltage: float = 0.0      # Volts
    battery_current: float = 0.0      # Amps (positive = discharge)
    battery_remaining: float = 1.0    # Ratio 0.0-1.0

    # Flight state
    flight_mode: FlightMode = FlightMode.UNKNOWN
    armed: bool = False
    health: VehicleHealth = VehicleHealth.UNKNOWN

    # GPS / positioning
    gps_fix_type: int = 0             # 0=no fix, 1=no fix, 2=2D, 3=3D, 4=DGPS, 5=RTK
    satellites_visible: int = 0
    hdop: float = 99.9                # Horizontal dilution of precision
    vdop: float = 99.9                # Vertical dilution of precision

    # Radio link
    rssi: float = -100.0              # dBm
    link_quality: float = 0.0         # 0.0-1.0

    # Raw data for debugging
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def is_stale(self, max_age_sec: float = 1.0) -> bool:
        """Check if telemetry is older than max_age_sec"""
        return (time.monotonic() - self.timestamp) > max_age_sec

    def position_ned(self) -> tuple[float, float, float]:
        """Get position in NED frame. Raises if not in NED frame."""
        if self.frame != CoordinateFrame.NED_LOCAL:
            raise ValueError(f"Position is in {self.frame.value}, not NED_LOCAL. Use convert_frame().")
        return self.position

    def velocity_ned(self) -> tuple[float, float, float]:
        """Get velocity in NED frame. Raises if not in NED frame."""
        if self.frame != CoordinateFrame.NED_LOCAL:
            raise ValueError(f"Velocity is in {self.frame.value}, not NED_LOCAL. Use convert_frame().")
        return self.velocity

    def distance_2d(self, other: 'VehicleTelemetry') -> float:
        """2D horizontal distance to another vehicle (requires both in NED)"""
        if self.frame != CoordinateFrame.NED_LOCAL or other.frame != CoordinateFrame.NED_LOCAL:
            raise ValueError("Both vehicles must be in NED_LOCAL frame")
        dx = self.position[0] - other.position[0]
        dy = self.position[1] - other.position[1]
        return math.hypot(dx, dy)

    def distance_3d(self, other: 'VehicleTelemetry') -> float:
        """3D distance to another vehicle (requires both in NED)"""
        if self.frame != CoordinateFrame.NED_LOCAL or other.frame != CoordinateFrame.NED_LOCAL:
            raise ValueError("Both vehicles must be in NED_LOCAL frame")
        dx = self.position[0] - other.position[0]
        dy = self.position[1] - other.position[1]
        dz = self.position[2] - other.position[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)


@dataclass
class VehicleState:
    """
    Aggregated vehicle state maintained by VehicleStateInterface.
    Combines latest telemetry with derived state for planning/safety.
    """
    vehicle_id: int
    telemetry: Optional[VehicleTelemetry] = None
    last_heartbeat: float = 0.0
    command_ack_pending: bool = False
    last_command_time: float = 0.0
    last_command_id: int = 0

    def is_telemetry_fresh(self, max_age_sec: float = 1.0) -> bool:
        if self.telemetry is None:
            return False
        return not self.telemetry.is_stale(max_age_sec)

    def get_position_ned(self) -> Optional[tuple[float, float, float]]:
        if self.telemetry and self.telemetry.frame == CoordinateFrame.NED_LOCAL:
            return self.telemetry.position
        return None

    def get_velocity_ned(self) -> Optional[tuple[float, float, float]]:
        if self.telemetry and self.telemetry.frame == CoordinateFrame.NED_LOCAL:
            return self.telemetry.velocity
        return None


class CoordinateConverter:
    """
    Coordinate frame conversions. Only these tested functions should be used.
    Do NOT hardcode lat/lon/elevation assumptions.
    """

    @staticmethod
    def ned_to_wgs84(ned_pos: tuple[float, float, float],
                      home_lat: float, home_lon: float, home_alt: float) -> tuple[float, float, float]:
        """
        Convert NED local position to WGS84 GPS.
        Uses simple flat-earth approximation valid for < ~10km from home.
        For precision applications, use a proper geodetic library.

        Args:
            ned_pos: (north, east, down) in meters from home
            home_lat: Home latitude in degrees
            home_lon: Home longitude in degrees
            home_alt: Home altitude in meters MSL

        Returns:
            (lat, lon, alt) in degrees, degrees, meters MSL
        """
        # Earth radius approximation
        R = 6378137.0

        north, east, down = ned_pos

        # Convert to lat/lon
        dlat = north / R
        dlon = east / (R * math.cos(math.radians(home_lat)))

        lat = home_lat + math.degrees(dlat)
        lon = home_lon + math.degrees(dlon)
        alt = home_alt - down  # Down is negative altitude

        return (lat, lon, alt)

    @staticmethod
    def wgs84_to_ned(wgs84_pos: tuple[float, float, float],
                      home_lat: float, home_lon: float, home_alt: float) -> tuple[float, float, float]:
        """
        Convert WGS84 GPS to NED local position.

        Args:
            wgs84_pos: (lat, lon, alt) in degrees, degrees, meters MSL
            home_lat: Home latitude in degrees
            home_lon: Home longitude in degrees
            home_alt: Home altitude in meters MSL

        Returns:
            (north, east, down) in meters from home
        """
        R = 6378137.0

        lat, lon, alt = wgs84_pos

        dlat = math.radians(lat - home_lat)
        dlon = math.radians(lon - home_lon)

        north = dlat * R
        east = dlon * R * math.cos(math.radians(home_lat))
        down = home_alt - alt

        return (north, east, down)

    @staticmethod
    def enu_to_ned(enu_pos: tuple[float, float, float]) -> tuple[float, float, float]:
        """Convert ENU to NED"""
        e, n, u = enu_pos
        return (n, e, -u)

    @staticmethod
    def ned_to_enu(ned_pos: tuple[float, float, float]) -> tuple[float, float, float]:
        """Convert NED to ENU"""
        n, e, d = ned_pos
        return (e, n, -d)

    @staticmethod
    def body_to_ned(body_vel: tuple[float, float, float],
                     roll: float, pitch: float, yaw: float) -> tuple[float, float, float]:
        """Convert body-frame velocity to NED frame using rotation matrix"""
        # Rotation matrix from body (FRD) to NED
        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)

        # R_body_to_ned
        r11 = cp * cy
        r12 = sr * sp * cy - cr * sy
        r13 = cr * sp * cy + sr * sy
        r21 = cp * sy
        r22 = sr * sp * sy + cr * cy
        r23 = cr * sp * sy - sr * cy
        r31 = -sp
        r32 = sr * cp
        r33 = cr * cp

        vx, vy, vz = body_vel
        vn = r11 * vx + r12 * vy + r13 * vz
        ve = r21 * vx + r22 * vy + r23 * vz
        vd = r31 * vx + r32 * vy + r33 * vz

        return (vn, ve, vd)


@dataclass
class ValidatedSetpoint:
    """
    A setpoint that has passed through the Command Validation Safety Layer.
    Only validated setpoints should be submitted to the AutopilotAdapter.
    """
    vehicle_id: int
    timestamp: float                      # Monotonic time when validated
    command_id: int                       # Unique command identifier

    # Target position (NED_LOCAL frame, meters)
    target_position_ned: tuple[float, float, float]

    # Optional velocity feedforward (NED_LOCAL frame, m/s)
    target_velocity_ned: Optional[tuple[float, float, float]] = None

    # Optional yaw target (radians, NED frame: 0=North, pi/2=East)
    target_yaw: Optional[float] = None

    # Mission deadline (monotonic time)
    deadline: Optional[float] = None

    # Authorization token for mode-changing commands
    authorization_token: Optional[str] = None

    def is_expired(self) -> bool:
        if self.deadline is None:
            return False
        return time.monotonic() > self.deadline

    def is_finite(self) -> bool:
        vals = list(self.target_position_ned)
        if self.target_velocity_ned:
            vals.extend(self.target_velocity_ned)
        if self.target_yaw is not None:
            vals.append(self.target_yaw)
        return all(math.isfinite(v) for v in vals)


@dataclass
class CommandAck:
    """Acknowledgement from autopilot for a submitted command"""
    command_id: int
    vehicle_id: int
    accepted: bool
    reason: str = ""
    timestamp: float = field(default_factory=time.monotonic)
    raw_response: Optional[Dict[str, Any]] = None


class RejectionReason(Enum):
    """Standardized rejection reasons for command validation"""
    TELEMETRY_STALE = "telemetry_stale"
    TELEMETRY_UNAVAILABLE = "telemetry_unavailable"
    SETPOINT_NON_FINITE = "setpoint_non_finite"
    SETPOINT_OUT_OF_BOUNDS = "setpoint_out_of_bounds"
    ALTITUDE_LIMIT_EXCEEDED = "altitude_limit_exceeded"
    VELOCITY_LIMIT_EXCEEDED = "velocity_limit_exceeded"
    UNSUPPORTED_FRAME = "unsupported_frame"
    UNKNOWN_VEHICLE = "unknown_vehicle"
    MODE_INCONSISTENT = "mode_inconsistent"
    COMMAND_EXPIRED = "command_expired"
    MISSION_DEADLINE_EXCEEDED = "mission_deadline_exceeded"
    MISSING_AUTHORIZATION = "missing_authorization"
    INVALID_COMMAND = "invalid_command"
    AUTOPILOT_UNHEALTHY = "autopilot_unhealthy"
    AUTOPILOT_UNSUPPORTED_STATE = "autopilot_unsupported_state"


@dataclass
class ValidationResult:
    """Result of command validation"""
    accepted: bool
    validated_setpoint: Optional[ValidatedSetpoint] = None
    rejection_reason: Optional[RejectionReason] = None
    rejection_details: str = ""
    timestamp: float = field(default_factory=time.monotonic)