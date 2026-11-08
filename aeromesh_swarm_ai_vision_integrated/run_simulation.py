"""AeroMesh Sprint CLI - --hardware / --sitl / --drone-id / --dashboard-port / --dry-run."""
import argparse, asyncio, time
from core.autopilot_interface.hybrid_adapter import HybridAutopilotAdapter
from swarm.failure_detector import FailureDetector
from core.ai_layer.explainable_logger import SwarmExplainableLogger
from comm.channel import MinifiedMeshChannel
from comm.mesh_udp import MeshUDPNode
from visualization.dashboard_server import start_dashboard, update_dashboard_data


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hardware", action="store_true")
    parser.add_argument("--sitl", action="store_true")
    parser.add_argument("--drone-id", type=int, default=1)
    parser.add_argument("--dashboard-port", type=int, default=8080)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--duration", type=float, default=3.0, help="Seconds to run before exit")
    args = parser.parse_args()

    adapter = HybridAutopilotAdapter()
    adapter.connect_interface()
    await adapter.wait_for_ekf_convergence(timeout=120)
    start_dashboard(port=args.dashboard_port)

    public_id = f"uav-{args.drone_id}"

    fd = FailureDetector()
    logger = SwarmExplainableLogger(public_id)
    ch = MinifiedMeshChannel(args.drone_id)
    mesh = MeshUDPNode()
    vision_hazard = {"current": "NONE"}

    async def flight_control_loop():
        async for pos in adapter.telemetry_stream():
            lat = pos["position"][0]
            lon = pos["position"][1]
            alt = pos["position"][2]
            hazard = vision_hazard["current"]

            pkt = ch.serialize_telemetry(lat, lon, alt, hazard)
            mesh.send(pkt)

            status = "SEARCHING" if args.dry_run else "HOLD"
            logger.log_decision(status, -72.0, hazard, "MAINTAIN_GRID" if args.dry_run else "HOLD")

            update_dashboard_data(public_id, lat, lon, alt, status)

            if args.dry_run:
                print("[BOOT] dry-run packet", pos)

            await asyncio.sleep(0.05)

    async def mesh_receive_loop():
        while True:
            now = time.monotonic()
            fd.update(args.drone_id, now)
            failed = fd.get_failed_drones(now)
            for d in failed:
                fd.on_failure(d)
                update_dashboard_data(f"uav-{d}", 0, 0, 0, "ALERT: heartbeat lost")
                logger.log_decision(str({"failed": d}), -50.0, "NONE", "REALLOC_STUB")
            await asyncio.sleep(1.0)

    async def vision_stub_loop():
        while True:
            vision_hazard["current"] = "HEAT" if args.dry_run else "NONE"
            await asyncio.sleep(1.0)

    try:
        await asyncio.wait_for(
            asyncio.gather(flight_control_loop(), mesh_receive_loop(), vision_stub_loop()),
            timeout=args.duration
        )
    except asyncio.TimeoutError:
        print("[BOOT] Duration reached, exiting cleanly")
        return
    except asyncio.CancelledError:
        print("[BOOT] Tasks cancelled cleanly")
        return


if __name__ == "__main__":
    asyncio.run(main())