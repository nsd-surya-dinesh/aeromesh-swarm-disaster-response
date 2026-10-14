"""AeroMesh-Swarm — Mission state bootstrap helper.

Creates a fully-populated MissionState for each scenario.
All ROS 2 nodes call bootstrap_mission_state() at startup so they
share the same UAV and PoI configuration.

This mirrors the Stage 1 scenario_builder.py without depending on the
full MissionSimulator (which we don't need in ROS 2 — nodes are separate
processes and Gazebo/PX4 will provide the vehicle state).
"""

from aeromesh_swarm.core.models import (
    UAV, UAVRole, UAVState, PointOfInterest, MissionState, Vector3D
)
from aeromesh_swarm.core.config import config

def _safe_enum(enum_class, *candidates):
    """Pick the first matching member of enum_class, else first member."""
    for name in candidates:
        if hasattr(enum_class, name):
            return getattr(enum_class, name)
    # fallback: first member of the enum
    members = list(enum_class)
    return members[0] if members else None




# ---------------------------------------------------------------
# Scenario definitions — mirror Stage 1 scenario_builder.py
# ---------------------------------------------------------------
SCENARIOS = {
    'S1': {
        'num_uavs': 5,
        'pois': [
            (300, 200), (450, 600), (700, 300), (850, 800), (200, 750),
            (-300, 400), (-500, 700), (-650, 200), (100, 950), (600, 1100),
        ],
        'priorities': [1.0, 2.0, 1.5, 3.0, 1.0, 1.2, 2.5, 1.0, 1.8, 2.2],
        'name': 'Baseline Survey',
    },
    'S2': {
        'num_uavs': 6,
        'pois': [
            (800, 800), (1000, 1000), (1200, 900), (1400, 1100),
            (1100, 1300), (1300, 1400), (1500, 1200), (1600, 1500),
        ],
        'priorities': [2.0, 3.0, 2.5, 4.0, 3.5, 5.0, 3.0, 4.5],
        'name': 'Deep Canyon',
    },
    'S3': {
        'num_uavs': 6,
        'pois': [
            (400, 400), (600, 600), (800, 400), (500, 800),
            (700, 900), (900, 700), (300, 600), (600, 300),
        ],
        'priorities': [1.5, 2.0, 2.5, 3.0, 2.8, 3.2, 2.0, 1.8],
        'name': 'Dynamic Fault',
    },
    'S4': {
        'num_uavs': 8,
        'pois': [
            (200, 200), (400, 400), (600, 200), (800, 400),
            (1000, 200), (1200, 400), (1400, 200), (1600, 400),
            (300, 800), (500, 1000), (700, 800), (900, 1000),
            (1100, 800), (1300, 1000), (1500, 800), (1700, 1000),
        ],
        'priorities': [1.0, 1.5, 1.2, 1.8, 1.3, 1.6, 1.4, 2.0,
                       2.2, 2.5, 2.3, 2.7, 2.4, 2.8, 2.6, 3.0],
        'name': 'Endurance',
    },
}


def bootstrap_mission_state(scenario: str = 'S1') -> MissionState:
    """Build and return a fully-populated MissionState.

    Args:
        scenario: One of 'S1', 'S2', 'S3', 'S4'.

    Returns:
        MissionState with UAVs and PoIs populated.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario}'. "
                         f"Expected one of {list(SCENARIOS.keys())}")

    cfg = SCENARIOS[scenario]
    state = MissionState()
    state.time = 0.0

    # GCS at origin (already default-constructed in MissionState)
    # Spawn UAVs in a ring around the GCS
    import math
    num = cfg['num_uavs']
    for i in range(num):
        angle = 2.0 * math.pi * i / num
        radius = 50.0  # initial spawn radius around GCS
        pos = Vector3D(
            x=radius * math.cos(angle),
            y=radius * math.sin(angle),
            z=50.0,   # 50 m cruise altitude
        )
        uav = UAV(
            id=i,
            position=pos,
            role=_safe_enum(UAVRole, 'SCOUT', 'SURVEYOR', 'IDLE'),
            state=_safe_enum(UAVState, 'ACTIVE', 'IDLE', 'READY', 'SURVEYING'),
        )
        state.uavs[i] = uav

    # Create PoIs
    for idx, (x, y) in enumerate(cfg['pois']):
        poi = PointOfInterest(
            id=idx,
            position=Vector3D(x=x, y=y, z=0.0),
            priority=cfg['priorities'][idx],
        )
        state.pois[idx] = poi

    return state


def get_scenario_name(scenario: str) -> str:
    """Return human-readable scenario name."""
    return SCENARIOS.get(scenario, {}).get('name', 'Unknown')
