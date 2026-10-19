import argparse
import csv
from collections import defaultdict
from pathlib import Path

from power_model import ProcessorPowerModel


SECONDS_PER_HOUR = 3600.0
WH_PER_KWH = 1000.0


def read_compute_attempts(
    intervals_path,
    site_id,
    simulation_time,
):
    """
    Read reconstructed compute intervals.

    Returns:
        attempts
        event_deltas

    event_deltas:
        processor_id -> {
            time -> delta_active_jobs
        }
    """

    intervals_path = Path(
        intervals_path
    )

    attempts = []

    event_deltas = defaultdict(
        lambda: defaultdict(int)
    )

    with intervals_path.open(
        "r",
        newline="",
    ) as csvfile:

        reader = csv.DictReader(
            csvfile
        )

        for row in reader:

            row_site_id = int(
                row["site_id"]
            )

            if row_site_id != site_id:
                continue

            processor_id = int(
                row["processor_id"]
            )

            start_time = float(
                row["start_time"]
            )

            end_time = float(
                row["end_time"]
            )

            if start_time < 0:
                raise ValueError(
                    f"Negative start time: "
                    f"{start_time}"
                )

            if end_time < start_time:
                raise ValueError(
                    "Compute interval ends "
                    "before it starts."
                )

            if end_time > simulation_time:
                raise ValueError(
                    f"Interval end {end_time} "
                    f"exceeds simulation time "
                    f"{simulation_time}"
                )

            attempts.append(
                {
                    "site_id":
                        row_site_id,
                    "processor_id":
                        processor_id,
                    "job_id":
                        int(row["job_id"]),
                    "attempt_id":
                        int(row["attempt_id"]),
                    "start_time":
                        start_time,
                    "end_time":
                        end_time,
                }
            )

            event_deltas[
                processor_id
            ][start_time] += 1

            event_deltas[
                processor_id
            ][end_time] -= 1

    return (
        attempts,
        event_deltas,
    )


def build_processor_power_trace(
    processor_id,
    site_id,
    simulation_time,
    event_deltas,
    power_model,
):
    """
    Build exact piecewise-constant processor power trace.

    Each row describes a time interval over which
    active_jobs and power are constant.
    """

    trace = []

    active_jobs = 0
    previous_time = 0.0

    deltas = event_deltas.get(
        processor_id,
        {},
    )

    event_times = sorted(
        time
        for time in deltas
        if 0 <= time <= simulation_time
    )

    total_energy_wh = 0.0
    total_busy_seconds = 0.0

    for time in event_times:

        if time > previous_time:

            duration_s = (
                time
                - previous_time
            )

            power_w = (
                power_model.power_w(
                    active_jobs
                )
            )

            utilization_proxy = (
                power_model.utilization_proxy(
                    active_jobs
                )
            )

            energy_wh = (
                power_w
                * duration_s
                / SECONDS_PER_HOUR
            )

            trace.append(
                {
                    "site_id":
                        site_id,
                    "processor_id":
                        processor_id,
                    "start_time":
                        previous_time,
                    "end_time":
                        time,
                    "duration_s":
                        duration_s,
                    "active_jobs":
                        active_jobs,
                    "utilization_proxy":
                        utilization_proxy,
                    "power_w":
                        power_w,
                    "energy_wh":
                        energy_wh,
                }
            )

            total_energy_wh += (
                energy_wh
            )

            if active_jobs > 0:
                total_busy_seconds += (
                    duration_s
                )

        active_jobs += (
            deltas[time]
        )

        if active_jobs < 0:
            raise ValueError(
                f"Processor {processor_id}: "
                f"active job count became "
                f"negative at time {time}"
            )

        previous_time = time

    # Integrate final interval to simulation end.
    if previous_time < simulation_time:

        duration_s = (
            simulation_time
            - previous_time
        )

        power_w = (
            power_model.power_w(
                active_jobs
            )
        )

        utilization_proxy = (
            power_model.utilization_proxy(
                active_jobs
            )
        )

        energy_wh = (
            power_w
            * duration_s
            / SECONDS_PER_HOUR
        )

        trace.append(
            {
                "site_id":
                    site_id,
                "processor_id":
                    processor_id,
                "start_time":
                    previous_time,
                "end_time":
                    simulation_time,
                "duration_s":
                    duration_s,
                "active_jobs":
                    active_jobs,
                "utilization_proxy":
                    utilization_proxy,
                "power_w":
                    power_w,
                "energy_wh":
                    energy_wh,
            }
        )

        total_energy_wh += (
            energy_wh
        )

        if active_jobs > 0:
            total_busy_seconds += (
                duration_s
            )

    return (
        trace,
        total_energy_wh,
        total_busy_seconds,
    )


def build_site_power_trace(
    site_id,
    simulation_time,
    num_processors,
    event_deltas,
    power_model,
):
    """
    Build site-level piecewise power trace.

    Site power is the sum of processor power.
    """

    all_times = {0.0, simulation_time}

    for processor_id in range(
        num_processors
    ):

        for time in event_deltas.get(
            processor_id,
            {},
        ):

            if 0 <= time <= simulation_time:
                all_times.add(time)

    times = sorted(
        all_times
    )

    active_jobs = {
        processor_id: 0
        for processor_id
        in range(num_processors)
    }

    trace = []

    total_energy_wh = 0.0

    for index in range(
        len(times) - 1
    ):

        current_time = (
            times[index]
        )

        next_time = (
            times[index + 1]
        )

        # Apply all events occurring at current_time
        # before calculating the interval that follows.
        for processor_id in range(
            num_processors
        ):

            delta = (
                event_deltas
                .get(processor_id, {})
                .get(current_time, 0)
            )

            active_jobs[
                processor_id
            ] += delta

            if (
                active_jobs[
                    processor_id
                ] < 0
            ):
                raise ValueError(
                    f"Processor "
                    f"{processor_id}: "
                    "negative active-job count."
                )

        duration_s = (
            next_time
            - current_time
        )

        if duration_s <= 0:
            continue

        processor_powers = []

        active_processors = 0
        total_active_jobs = 0

        for processor_id in range(
            num_processors
        ):

            count = active_jobs[
                processor_id
            ]

            power = (
                power_model.power_w(
                    count
                )
            )

            processor_powers.append(
                power
            )

            total_active_jobs += (
                count
            )

            if count > 0:
                active_processors += 1

        site_power_w = sum(
            processor_powers
        )

        energy_wh = (
            site_power_w
            * duration_s
            / SECONDS_PER_HOUR
        )

        trace.append(
            {
                "site_id":
                    site_id,
                "start_time":
                    current_time,
                "end_time":
                    next_time,
                "duration_s":
                    duration_s,
                "active_processors":
                    active_processors,
                "total_active_jobs":
                    total_active_jobs,
                "site_power_w":
                    site_power_w,
                "energy_wh":
                    energy_wh,
            }
        )

        total_energy_wh += (
            energy_wh
        )

    return (
        trace,
        total_energy_wh,
    )


def write_csv(
    path,
    rows,
):
    """
    Write list of dictionaries to CSV.
    """

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not rows:
        return

    with path.open(
        "w",
        newline="",
    ) as csvfile:

        writer = csv.DictWriter(
            csvfile,
            fieldnames=rows[0].keys(),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def run_energy_analysis(
    intervals_path,
    simulation_time,
    num_processors,
    site_id,
    idle_power_w,
    active_power_w,
    output_dir,
):
    """
    Generate processor/site power traces and
    integrate energy.
    """

    power_model = (
        ProcessorPowerModel(
            idle_power_w=
                idle_power_w,
            active_power_w=
                active_power_w,
        )
    )

    (
        attempts,
        event_deltas,
    ) = read_compute_attempts(
        intervals_path=
            intervals_path,
        site_id=
            site_id,
        simulation_time=
            simulation_time,
    )

    processor_trace = []
    processor_summary = []

    total_processor_energy_wh = 0.0
    total_busy_seconds = 0.0

    for processor_id in range(
        num_processors
    ):

        (
            trace,
            energy_wh,
            busy_seconds,
        ) = build_processor_power_trace(
            processor_id=
                processor_id,
            site_id=
                site_id,
            simulation_time=
                simulation_time,
            event_deltas=
                event_deltas,
            power_model=
                power_model,
        )

        processor_trace.extend(
            trace
        )

        baseline_idle_energy_wh = (
            idle_power_w
            * simulation_time
            / SECONDS_PER_HOUR
        )

        activity_increment_energy_wh = (
            (
                active_power_w
                - idle_power_w
            )
            * busy_seconds
            / SECONDS_PER_HOUR
        )

        processor_summary.append(
            {
                "site_id":
                    site_id,
                "processor_id":
                    processor_id,
                "simulation_time_s":
                    simulation_time,
                "busy_seconds":
                    busy_seconds,
                "activity_percent":
                    (
                        busy_seconds
                        / simulation_time
                        * 100.0
                    ),
                "idle_power_w":
                    idle_power_w,
                "active_power_w":
                    active_power_w,
                "baseline_idle_energy_wh":
                    baseline_idle_energy_wh,
                "activity_increment_energy_wh":
                    activity_increment_energy_wh,
                "total_energy_wh":
                    energy_wh,
                "total_energy_kwh":
                    (
                        energy_wh
                        / WH_PER_KWH
                    ),
            }
        )

        total_processor_energy_wh += (
            energy_wh
        )

        total_busy_seconds += (
            busy_seconds
        )

    (
        site_trace,
        site_energy_wh,
    ) = build_site_power_trace(
        site_id=
            site_id,
        simulation_time=
            simulation_time,
        num_processors=
            num_processors,
        event_deltas=
            event_deltas,
        power_model=
            power_model,
    )

    # Independent analytical cross-check.
    expected_energy_wh = (
        (
            num_processors
            * idle_power_w
            * simulation_time
        )
        +
        (
            (
                active_power_w
                - idle_power_w
            )
            * total_busy_seconds
        )
    ) / SECONDS_PER_HOUR

    tolerance = 1e-9

    if abs(
        site_energy_wh
        - expected_energy_wh
    ) > tolerance:

        raise ValueError(
            "Energy validation failed: "
            f"trace={site_energy_wh}, "
            f"analytical="
            f"{expected_energy_wh}"
        )

    if abs(
        site_energy_wh
        - total_processor_energy_wh
    ) > tolerance:

        raise ValueError(
            "Processor/site energy "
            "aggregation mismatch."
        )

    average_site_power_w = (
        site_energy_wh
        * SECONDS_PER_HOUR
        / simulation_time
    )

    peak_site_power_w = max(
        (
            row["site_power_w"]
            for row in site_trace
        ),
        default=(
            num_processors
            * idle_power_w
        ),
    )

    baseline_site_energy_wh = (
        num_processors
        * idle_power_w
        * simulation_time
        / SECONDS_PER_HOUR
    )

    activity_increment_energy_wh = (
        site_energy_wh
        - baseline_site_energy_wh
    )

    site_summary = [
        {
            "site_id":
                site_id,
            "simulation_time_s":
                simulation_time,
            "num_processors":
                num_processors,
            "idle_power_w_per_processor":
                idle_power_w,
            "active_power_w_per_processor":
                active_power_w,
            "total_processor_busy_seconds":
                total_busy_seconds,
            "baseline_idle_energy_wh":
                baseline_site_energy_wh,
            "activity_increment_energy_wh":
                activity_increment_energy_wh,
            "total_energy_wh":
                site_energy_wh,
            "total_energy_kwh":
                (
                    site_energy_wh
                    / WH_PER_KWH
                ),
            "average_site_power_w":
                average_site_power_w,
            "peak_site_power_w":
                peak_site_power_w,
        }
    ]

    output_dir = Path(
        output_dir
    )

    write_csv(
        output_dir
        / "processor_power_trace.csv",
        processor_trace,
    )

    write_csv(
        output_dir
        / "site_power_trace.csv",
        site_trace,
    )

    write_csv(
        output_dir
        / "processor_energy_summary.csv",
        processor_summary,
    )

    write_csv(
        output_dir
        / "site_energy_summary.csv",
        site_summary,
    )

    return {
        "attempts":
            attempts,
        "processor_trace":
            processor_trace,
        "site_trace":
            site_trace,
        "processor_summary":
            processor_summary,
        "site_summary":
            site_summary[0],
    }


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Green DISTRI processor "
            "power and energy analysis."
        )
    )

    parser.add_argument(
        "--intervals",
        required=True,
        help=(
            "Path to "
            "compute_attempt_intervals.csv"
        ),
    )

    parser.add_argument(
        "--simulation-time",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--num-processors",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--site-id",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--idle-power-w",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--active-power-w",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    args = parser.parse_args()

    result = run_energy_analysis(
        intervals_path=
            args.intervals,
        simulation_time=
            args.simulation_time,
        num_processors=
            args.num_processors,
        site_id=
            args.site_id,
        idle_power_w=
            args.idle_power_w,
        active_power_w=
            args.active_power_w,
        output_dir=
            args.output_dir,
    )

    site = result[
        "site_summary"
    ]

    print()
    print(
        "Green DISTRI "
        "Power/Energy Results"
    )
    print("=" * 64)

    print(
        f"Simulation time: "
        f"{site['simulation_time_s']:.2f} s"
    )

    print(
        f"Processors: "
        f"{site['num_processors']}"
    )

    print(
        f"Idle power / processor: "
        f"{site['idle_power_w_per_processor']:.2f} W"
    )

    print(
        f"Active power / processor: "
        f"{site['active_power_w_per_processor']:.2f} W"
    )

    print(
        f"Total processor busy time: "
        f"{site['total_processor_busy_seconds']:.4f} s"
    )

    print("-" * 64)

    print(
        f"Idle baseline energy: "
        f"{site['baseline_idle_energy_wh']:.6f} Wh"
    )

    print(
        f"Activity increment energy: "
        f"{site['activity_increment_energy_wh']:.6f} Wh"
    )

    print(
        f"Total site energy: "
        f"{site['total_energy_wh']:.6f} Wh"
    )

    print(
        f"Total site energy: "
        f"{site['total_energy_kwh']:.9f} kWh"
    )

    print(
        f"Average site power: "
        f"{site['average_site_power_w']:.3f} W"
    )

    print(
        f"Peak site power: "
        f"{site['peak_site_power_w']:.3f} W"
    )

    print("=" * 64)


if __name__ == "__main__":
    main()