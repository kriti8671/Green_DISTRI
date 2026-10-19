import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read_csv(path):
    """
    Read a CSV file and return all rows as dictionaries.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    with path.open("r", newline="") as csvfile:
        return list(csv.DictReader(csvfile))


# ============================================================
# FIGURE 1
#
# Dynamic relationship:
#
# Active Processors
#       ↓
# Site Processor Power
#       ↓
# Cumulative Processor Energy
# ============================================================


def plot_dynamic_pipeline(
    site_power_trace_path,
    site_energy_summary_path,
    output_dir,
):
    """
    Generate a synchronized three-panel figure:

        1. Active processors over time
        2. Site processor power over time
        3. Cumulative processor energy over time

    All plots share the same simulation-time x-axis.
    """

    trace_rows = read_csv(
        site_power_trace_path
    )

    energy_rows = read_csv(
        site_energy_summary_path
    )

    if not trace_rows:
        raise ValueError(
            "site_power_trace.csv contains no data."
        )

    if not energy_rows:
        raise ValueError(
            "site_energy_summary.csv contains no data."
        )

    summary = energy_rows[0]

    # --------------------------------------------------------
    # Reconstruct the piecewise time-series.
    # --------------------------------------------------------

    start_times = [
        float(row["start_time"])
        for row in trace_rows
    ]

    final_time = float(
        trace_rows[-1]["end_time"]
    )

    times = (
        start_times
        + [final_time]
    )

    active_processors = [
        int(row["active_processors"])
        for row in trace_rows
    ]

    active_processors.append(
        active_processors[-1]
    )

    site_power = [
        float(row["site_power_w"])
        for row in trace_rows
    ]

    site_power.append(
        site_power[-1]
    )

    # --------------------------------------------------------
    # Cumulative energy.
    #
    # Energy is already calculated for every power interval:
    #
    # E_i = P_i * delta_t_i / 3600
    # --------------------------------------------------------

    cumulative_times = [
        float(trace_rows[0]["start_time"])
    ]

    cumulative_energy = [0.0]

    running_energy = 0.0

    for row in trace_rows:

        running_energy += float(
            row["energy_wh"]
        )

        cumulative_times.append(
            float(row["end_time"])
        )

        cumulative_energy.append(
            running_energy
        )

    # --------------------------------------------------------
    # Summary values for annotations.
    # --------------------------------------------------------

    idle_power = float(
        summary[
            "idle_power_w_per_processor"
        ]
    )

    active_power = float(
        summary[
            "active_power_w_per_processor"
        ]
    )

    total_energy = float(
        summary["total_energy_wh"]
    )

    average_power = float(
        summary["average_site_power_w"]
    )

    peak_power = float(
        summary["peak_site_power_w"]
    )

    num_processors = int(
        summary["num_processors"]
    )

    idle_site_power = (
        idle_power
        * num_processors
    )

    # --------------------------------------------------------
    # Create synchronized figure.
    # --------------------------------------------------------

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(12, 10),
        sharex=True,
    )

    fig.suptitle(
        "Green DISTRI — Compute Activity, Power, and Energy",
        fontsize=16,
    )

    # ========================================================
    # Panel A — Active processors
    # ========================================================

    ax1 = axes[0]

    ax1.step(
        times,
        active_processors,
        where="post",
        linewidth=1.6,
    )

    ax1.set_ylabel(
        "Active\nProcessors"
    )

    ax1.set_title(
        "(a) Compute Activity"
    )

    ax1.set_ylim(
        bottom=0
    )

    ax1.grid(
        True,
        alpha=0.25,
    )

    peak_active = max(
        active_processors
    )

    ax1.text(
        0.99,
        0.88,
        (
            f"Peak active processors = "
            f"{peak_active}"
        ),
        transform=ax1.transAxes,
        ha="right",
        va="top",
    )

    # ========================================================
    # Panel B — Site processor power
    # ========================================================

    ax2 = axes[1]

    ax2.step(
        times,
        site_power,
        where="post",
        linewidth=1.6,
    )

    ax2.axhline(
        idle_site_power,
        linestyle="--",
        linewidth=1.0,
        label=(
            f"Idle baseline "
            f"({idle_site_power:.0f} W)"
        ),
    )

    ax2.set_ylabel(
        "Processor\nPower (W)"
    )

    ax2.set_title(
        "(b) Site Processor Power"
    )

    ax2.grid(
        True,
        alpha=0.25,
    )

    ax2.legend(
        loc="upper right"
    )

    ax2.text(
        0.99,
        0.68,
        (
            f"Average = "
            f"{average_power:.1f} W\n"
            f"Peak = "
            f"{peak_power:.1f} W"
        ),
        transform=ax2.transAxes,
        ha="right",
        va="top",
    )

    # ========================================================
    # Panel C — Cumulative energy
    # ========================================================

    ax3 = axes[2]

    ax3.plot(
        cumulative_times,
        cumulative_energy,
        linewidth=1.8,
    )

    ax3.set_xlabel(
        "Simulation Time (s)"
    )

    ax3.set_ylabel(
        "Cumulative\nEnergy (Wh)"
    )

    ax3.set_title(
        "(c) Cumulative Processor Energy"
    )

    ax3.set_ylim(
        bottom=0
    )

    ax3.grid(
        True,
        alpha=0.25,
    )

    ax3.text(
        0.99,
        0.10,
        (
            f"Total = "
            f"{total_energy:.2f} Wh"
        ),
        transform=ax3.transAxes,
        ha="right",
        va="bottom",
    )

    # --------------------------------------------------------
    # Model-assumption annotation.
    # --------------------------------------------------------

    fig.text(
        0.5,
        0.01,
        (
            "MVP activity-based power model: "
            f"P_idle = {idle_power:.0f} W, "
            f"P_active = {active_power:.0f} W per processor"
        ),
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[0, 0.035, 1, 0.96]
    )

    png_path = (
        output_dir
        / "mvp_activity_power_energy.png"
    )

    pdf_path = (
        output_dir
        / "mvp_activity_power_energy.pdf"
    )

    fig.savefig(
        png_path,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        pdf_path,
        bbox_inches="tight",
    )

    plt.close(fig)

    return (
        png_path,
        pdf_path,
    )


# ============================================================
# FIGURE 2
#
# Per-processor relationship:
#
# Activity percentage
#       ↕
# Idle + activity energy
# ============================================================


def plot_processor_activity_energy(
    processor_activity_path,
    processor_energy_path,
    output_dir,
):
    """
    Generate a two-panel processor-level figure:

        A. Compute activity percentage
        B. Processor energy breakdown

    The same processor ordering is used in both panels.
    """

    activity_rows = read_csv(
        processor_activity_path
    )

    energy_rows = read_csv(
        processor_energy_path
    )

    if not activity_rows:
        raise ValueError(
            "processor_activity_metrics.csv "
            "contains no data."
        )

    if not energy_rows:
        raise ValueError(
            "processor_energy_summary.csv "
            "contains no data."
        )

    # --------------------------------------------------------
    # Build processor lookup.
    # --------------------------------------------------------

    activity_lookup = {
        int(row["processor_id"]): row
        for row in activity_rows
    }

    energy_lookup = {
        int(row["processor_id"]): row
        for row in energy_rows
    }

    processor_ids = sorted(
        set(activity_lookup)
        & set(energy_lookup)
    )

    if not processor_ids:
        raise ValueError(
            "No matching processors were found "
            "between activity and energy files."
        )

    labels = [
        f"P{processor_id}"
        for processor_id
        in processor_ids
    ]

    activity_percent = [
        float(
            activity_lookup[
                processor_id
            ]["activity_percent"]
        )
        for processor_id
        in processor_ids
    ]

    idle_energy = [
        float(
            energy_lookup[
                processor_id
            ]["baseline_idle_energy_wh"]
        )
        for processor_id
        in processor_ids
    ]

    activity_energy = [
        float(
            energy_lookup[
                processor_id
            ][
                "activity_increment_energy_wh"
            ]
        )
        for processor_id
        in processor_ids
    ]

    total_energy = [
        idle + activity
        for idle, activity
        in zip(
            idle_energy,
            activity_energy,
        )
    ]

    # --------------------------------------------------------
    # Create figure.
    # --------------------------------------------------------

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(11, 9),
        sharex=True,
    )

    fig.suptitle(
        "Green DISTRI — Processor Activity and Energy",
        fontsize=16,
    )

    # ========================================================
    # Panel A — Processor activity
    # ========================================================

    ax1 = axes[0]

    bars_activity = ax1.bar(
        labels,
        activity_percent,
    )

    ax1.set_ylabel(
        "Compute Activity (%)"
    )

    ax1.set_title(
        "(a) Processor Compute Activity"
    )

    ax1.set_ylim(
        bottom=0
    )

    ax1.grid(
        axis="y",
        alpha=0.25,
    )

    for bar, value in zip(
        bars_activity,
        activity_percent,
    ):

        ax1.text(
            bar.get_x()
            + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    # ========================================================
    # Panel B — Processor energy
    # ========================================================

    ax2 = axes[1]

    bars_idle = ax2.bar(
        labels,
        idle_energy,
        label="Idle baseline energy",
    )

    bars_activity_energy = ax2.bar(
        labels,
        activity_energy,
        bottom=idle_energy,
        label="Activity increment energy",
    )

    ax2.set_xlabel(
        "Processor"
    )

    ax2.set_ylabel(
        "Energy (Wh)"
    )

    ax2.set_title(
        "(b) Processor Energy Breakdown"
    )

    ax2.grid(
        axis="y",
        alpha=0.25,
    )

    ax2.legend()

    # --------------------------------------------------------
    # Put total energy above each stacked bar.
    # --------------------------------------------------------

    for bar, value in zip(
        bars_activity_energy,
        total_energy,
    ):

        processor_index = (
            list(
                bars_activity_energy
            ).index(bar)
        )

        top = total_energy[
            processor_index
        ]

        ax2.text(
            bar.get_x()
            + bar.get_width() / 2,
            top,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout(
        rect=[0, 0.02, 1, 0.96]
    )

    png_path = (
        output_dir
        / "processor_activity_energy.png"
    )

    pdf_path = (
        output_dir
        / "processor_activity_energy.pdf"
    )

    fig.savefig(
        png_path,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        pdf_path,
        bbox_inches="tight",
    )

    plt.close(fig)

    return (
        png_path,
        pdf_path,
    )


# ============================================================
# MAIN
# ============================================================


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate combined Green DISTRI "
            "activity, power, and energy plots."
        )
    )

    parser.add_argument(
        "--gdcs-dir",
        required=True,
        help=(
            "Directory containing Green DISTRI "
            "CSV outputs."
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory for combined plots. "
            "Default: <gdcs-dir>/plots"
        ),
    )

    args = parser.parse_args()

    gdcs_dir = Path(
        args.gdcs_dir
    )

    if args.output_dir:
        output_dir = Path(
            args.output_dir
        )
    else:
        output_dir = (
            gdcs_dir
            / "plots"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Required Green DISTRI output files.
    # --------------------------------------------------------

    site_power_trace_path = (
        gdcs_dir
        / "site_power_trace.csv"
    )

    site_energy_summary_path = (
        gdcs_dir
        / "site_energy_summary.csv"
    )

    processor_activity_path = (
        gdcs_dir
        / "processor_activity_metrics.csv"
    )

    processor_energy_path = (
        gdcs_dir
        / "processor_energy_summary.csv"
    )

    print()
    print(
        "Generating combined "
        "Green DISTRI plots..."
    )

    print("=" * 68)

    # --------------------------------------------------------
    # Figure 1
    # --------------------------------------------------------

    dynamic_png, dynamic_pdf = (
        plot_dynamic_pipeline(
            site_power_trace_path=
                site_power_trace_path,
            site_energy_summary_path=
                site_energy_summary_path,
            output_dir=
                output_dir,
        )
    )

    print(
        "Dynamic activity → power → energy:"
    )

    print(
        f"  {dynamic_png}"
    )

    print(
        f"  {dynamic_pdf}"
    )

    print()

    # --------------------------------------------------------
    # Figure 2
    # --------------------------------------------------------

    processor_png, processor_pdf = (
        plot_processor_activity_energy(
            processor_activity_path=
                processor_activity_path,
            processor_energy_path=
                processor_energy_path,
            output_dir=
                output_dir,
        )
    )

    print(
        "Processor activity ↔ energy:"
    )

    print(
        f"  {processor_png}"
    )

    print(
        f"  {processor_pdf}"
    )

    print("=" * 68)


if __name__ == "__main__":
    main()