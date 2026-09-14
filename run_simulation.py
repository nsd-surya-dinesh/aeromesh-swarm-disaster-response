"""
AeroMesh-Swarm Main CLI Runner
Supports running simulation scenarios, interactive GUI, and generating benchmarks.
"""
import argparse
import sys
import os
from simulation.scenario_builder import ScenarioBuilder
from simulation.metrics import MetricsEngine
from simulation.challenge_metrics import ChallengeMetricsReporter
from visualization.video_recorder import VideoRecorder
from visualization.plotter import ChartPlotter

# Optional pygame import
try:
    from visualization.gui_visualizer import GUIVisualizer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    GUIVisualizer = None


def print_metrics_summary(metrics):
    """Prints formatted metrics summary"""
    print("\n[+] Mission Execution Summary:")
    print("-------------------------------------------------------")
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"  {k:35s}: {v:.2f}")
        else:
            print(f"  {k:35s}: {v}")
    print("-------------------------------------------------------\n")


def main():
    parser = argparse.ArgumentParser(description="AeroMesh-Swarm: UAV Swarm Disaster Response System")
    parser.add_argument("--scenario", type=int, default=1, choices=[1, 2, 3, 4],
                        help="Scenario to run: 1=Baseline, 2=Deep Canyon, 3=Dynamic Fault, 4=Endurance")
    parser.add_argument("--gui", action="store_true", help="Launch interactive Pygame GUI")
    parser.add_argument("--record", action="store_true", help="Record simulation to video/GIF")
    parser.add_argument("--max-time", type=float, default=600.0, help="Max simulation duration (seconds)")
    parser.add_argument("--benchmark-all", action="store_true", help="Run all 4 scenarios and output comparison")

    args = parser.parse_args()

    if args.benchmark_all:
        run_all_benchmarks()
        return

    # Build selected scenario
    sim_builders = {
        1: ScenarioBuilder.scenario_1_baseline_survey,
        2: ScenarioBuilder.scenario_2_deep_canyon_los_blockage,
        3: ScenarioBuilder.scenario_3_dynamic_emergency_and_node_failure,
        4: ScenarioBuilder.scenario_4_continuous_swapping_endurance
    }

    print(f"\n=======================================================")
    print(f">> AeroMesh-Swarm: Launching Scenario {args.scenario}")
    print(f"=======================================================")

    sim = sim_builders[args.scenario]()

    if args.gui:
        if not PYGAME_AVAILABLE:
            print("[-] Pygame not installed. GUI mode requires pygame.")
            print("    Install with: pip install pygame")
            print("    Running in headless mode instead...\n")
            report = sim.run_simulation(max_time=args.max_time)
            metrics = MetricsEngine(sim.mission_state).generate_full_metrics_summary()
            print_metrics_summary(metrics)
        else:
            print(">> Starting interactive Pygame visualizer...")
            visualizer = GUIVisualizer(sim)
            visualizer.run(max_time=args.max_time)
    elif args.record:
        print(">> Starting headless video recording...")
        recorder = VideoRecorder(sim)
        recorder.run_and_record(max_time=args.max_time)
        recorder.export_video(f"scenario_{args.scenario}_demo.mp4")
    else:
        # Headless fast simulation
        report = sim.run_simulation(max_time=args.max_time)

        # Generate comprehensive challenge-compliant metrics report
        challenge_reporter = ChallengeMetricsReporter(sim.mission_state)
        challenge_reporter.print_challenge_report()


def run_all_benchmarks():
    """Runs all 4 scenarios headlessly and generates comparative benchmark report"""
    print("\n=== Running Comprehensive Benchmark Suite Across All 4 Scenarios ===\n")

    scenarios = [
        ("Scenario 1: Baseline", ScenarioBuilder.scenario_1_baseline_survey),
        ("Scenario 2: Deep Canyon", ScenarioBuilder.scenario_2_deep_canyon_los_blockage),
        ("Scenario 3: Dynamic Fault", ScenarioBuilder.scenario_3_dynamic_emergency_and_node_failure),
        ("Scenario 4: Endurance", ScenarioBuilder.scenario_4_continuous_swapping_endurance),
    ]

    all_metrics = []
    names = []

    for name, builder in scenarios:
        print(f">> Executing {name}...")
        sim = builder()
        sim.run_simulation(max_time=600.0)
        metrics = MetricsEngine(sim.mission_state).generate_full_metrics_summary()
        all_metrics.append(metrics)
        names.append(name)

    print("\n" + "="*80)
    print("BENCHMARK COMPARISON MATRIX")
    print("="*80)
    print(f"{'Metric':<32} | {'S1: Baseline':<12} | {'S2: Canyon':<12} | {'S3: Fault':<12} | {'S4: Endurance':<12}")
    print("-"*80)

    keys = [
        ('Coverage (%)', 'coverage_percentage'),
        ('PDR (%)', 'packet_delivery_ratio_pdr'),
        ('Avg Latency (ms)', 'avg_end_to_end_latency_ms'),
        ('PoIs Surveyed', 'pois_surveyed'),
        ('Total Energy (kWh)', 'total_energy_kwh'),
        ('Survey Rate (PoI/min)', 'survey_rate_pois_per_min'),
        ('Survival Rate (%)', 'swarm_survival_rate')
    ]

    for label, key in keys:
        vals = [f"{m[key]:.1f}" for m in all_metrics]
        print(f"{label:<32} | {vals[0]:<12} | {vals[1]:<12} | {vals[2]:<12} | {vals[3]:<12}")

    print("="*80)

    # Generate charts if docs/figures exists
    os.makedirs("docs/figures", exist_ok=True)
    plotter = ChartPlotter("docs/figures")
    plotter.plot_scenario_comparison(names, all_metrics)
    print(">> Generated comparative charts in docs/figures/scenario_comparison.png\n")


if __name__ == "__main__":
    main()
