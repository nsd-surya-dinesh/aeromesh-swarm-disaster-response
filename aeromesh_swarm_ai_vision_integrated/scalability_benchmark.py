#!/usr/bin/env python3
"""
Scalability Benchmark for AeroMesh-Swarm
Tests performance with varying UAV counts: 5, 10, 15, 20, 25
Measures runtime, PDR, latency, coverage, and CBBA performance
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation.scenario_builder import ScenarioBuilder
from simulation.metrics import MetricsEngine
from core.models import MissionState
import numpy as np


def run_scalability_benchmark():
    """Run benchmark with varying UAV counts"""
    print("=== AeroMesh-Swarm Scalability Benchmark ===")
    print("Testing UAV counts: 5, 10, 15, 20, 25")
    print("=" * 60)

    # Fixed scenario parameters for fair comparison
    area_size = 2000.0  # meters
    num_pois = 10       # Fixed number of PoIs

    results = []

    for num_uavs in [5, 10, 15, 20, 25]:
        print(f"\n>> Testing with {num_uavs} UAVs and {num_pois} PoIs...")

        # Create scenario builder with fixed parameters
        class FixedScenarioBuilder:
            @staticmethod
            def scenario_baseline_survey():
                sim = ScenarioBuilder.scenario_1_baseline_survey()
                # Override the initialized UAVs and PoIs
                sim.mission_state.uavs.clear()
                sim.mission_state.pois.clear()

                # Initialize UAVs at GCS
                gcs_pos = sim.mission_state.gcs.position
                for i in range(num_uavs):
                    uav_pos = Vector3D(
                        gcs_pos.x + np.random.uniform(-50, 50),
                        gcs_pos.y + np.random.uniform(-50, 50),
                        0.0
                    )
                    uav = UAV(
                        id=i,
                        position=uav_pos,
                        role=UAVRole.STANDBY,
                        state=UAVState.IDLE,
                        battery_level=1.0
                    )
                    sim.mission_state.uavs[i] = uav

                # Initialize PoIs in a grid pattern
                poi_positions = []
                pois_per_side = int(np.ceil(np.sqrt(num_pois)))
                spacing = area_size / (pois_per_side + 1)

                for i in range(num_pois):
                    row = i // pois_per_side
                    col = i % pois_per_side
                    x = spacing * (col + 1) + np.random.uniform(-spacing/4, spacing/4)
                    y = spacing * (row + 1) + np.random.uniform(-spacing/4, spacing/4)
                    poi_positions.append(Vector3D(x, y, 0.0))

                for i, pos in enumerate(poi_positions):
                    poi = PointOfInterest(
                        id=i,
                        position=pos,
                        priority=1.0 + (i % 3)  # Vary priority 1.0-3.0
                    )
                    sim.mission_state.pois[i] = poi

                sim.mission_state.gcs.total_pois_discovered = len(poi_positions)
                return sim

        # Import required classes inside function to avoid issues
        from core.models import Vector3D, UAV, UAVRole, UAVState, PointOfInterest

        # Create and run simulation
        sim = FixedScenarioBuilder.scenario_baseline_survey()

        start_time = time.time()
        sim.run_simulation(max_time=300.0)  # 5 minute limit
        end_time = time.time()

        runtime = end_time - start_time

        # Collect metrics
        metrics_engine = MetricsEngine(sim.mission_state)
        metrics = metrics_engine.generate_full_metrics_summary()

        # Get additional metrics
        network_stats = sim.mesh_router.get_network_stats()
        gcs = sim.mission_state.gcs
        packets_sent = gcs.packets_received + gcs.packets_dropped
        packets_delivered = gcs.packets_received
        packets_dropped = gcs.packets_dropped
        avg_hops = network_stats['avg_hops']

        # CBBA performance metrics (actual from allocator)
        cbba_iterations = getattr(sim.task_allocator, 'last_iteration_count', 0)

        result = {
            'uav_count': num_uavs,
            'runtime_s': runtime,
            'coverage_percent': metrics['coverage_percentage'],
            'pdr_percent': metrics['packet_delivery_ratio_pdr'],
            'avg_latency_ms': metrics['avg_end_to_end_latency_ms'],
            'packets_sent': packets_sent,
            'packets_delivered': packets_delivered,
            'packets_dropped': packets_dropped,
            'avg_hops': avg_hops,
            'cbba_iterations': cbba_iterations,
            'pois_surveyed': metrics['pois_surveyed'],
            'total_pois': metrics['total_pois']
        }

        results.append(result)

        # Print immediate feedback
        print(f"   Runtime: {runtime:.2f}s")
        print(f"   Coverage: {metrics['coverage_percentage']:.1f}%")
        print(f"   PDR: {metrics['packet_delivery_ratio_pdr']:.1f}%")
        print(f"   Latency: {metrics['avg_end_to_end_latency_ms']:.1f} ms")
        print(f"   Avg Hops: {avg_hops:.1f}")

    # Print summary table
    print("\n" + "=" * 80)
    print("SCALABILITY BENCHMARK RESULTS")
    print("=" * 80)
    print(f"{'UAVs':<6} | {'Runtime(s)':<10} | {'Coverage(%)':<12} | {'PDR(%)':<8} | {'Latency(ms)':<12} | {'Avg Hops':<8} | {'CBBA Iters':<10}")
    print("-" * 80)

    for r in results:
        print(f"{r['uav_count']:<6} | {r['runtime_s']:<10.2f} | {r['coverage_percent']:<12.1f} | {r['pdr_percent']:<8.1f} | {r['avg_latency_ms']:<12.1f} | {r['avg_hops']:<8.1f} | {r['cbba_iterations']:<10}")

    print("=" * 80)

    # Save results to file
    with open('scalability_benchmark_results.txt', 'w') as f:
        f.write("AeroMesh-Swarm Scalability Benchmark Results\n")
        f.write("=" * 50 + "\n\n")
        for r in results:
            f.write(f"UAV Count: {r['uav_count']}\n")
            f.write(f"  Runtime: {r['runtime_s']:.2f} s\n")
            f.write(f"  Coverage: {r['coverage_percent']:.1f}%\n")
            f.write(f"  PDR: {r['pdr_percent']:.1f}%\n")
            f.write(f"  Avg Latency: {r['avg_latency_ms']:.1f} ms\n")
            f.write(f"  Packets Sent: {r['packets_sent']}\n")
            f.write(f"  Packets Delivered: {r['packets_delivered']}\n")
            f.write(f"  Packets Dropped: {r['packets_dropped']}\n")
            f.write(f"  Avg Hops: {r['avg_hops']:.1f}\n")
            f.write(f"  CBBA Iterations: {r['cbba_iterations']}\n")
            f.write(f"  PoIs Surveyed: {r['pois_surveyed']}/{r['total_pois']}\n")
            f.write("\n")

    print("\n>> Results saved to scalability_benchmark_results.txt")
    return results


if __name__ == "__main__":
    run_scalability_benchmark()