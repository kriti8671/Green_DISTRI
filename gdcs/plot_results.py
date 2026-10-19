import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read_csv(path):
    with open(path, "r", newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def plot_site_power_trace(
    site_power_trace_path,
    output_dir,
):
    """
    Plot piecewise-constant site power over simulation time.
    """

    rows = read_csv(site_power_trace_path)

    if not rows:
        raise ValueError(
            "site_power_trace.csv contains no data."
        )

    times = []
    powers = []

    for index, row in enumerate(rows):

        start_time = float(row["start_time"])
        end_time = float(row["end_time"])
        power_w = float(row["site_power_w"])

        if index == 0:
            times.append(start_time)
            powers.append(power_w)

        times.append(end_time)
        powers.append(power_w)

    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    ax.step(
        times,
        powers,
        where="post",
        linewidth=1.5,
    )

    ax.set_xlabel(
        "Simulation Time (s)"
    )

    ax.set_ylabel(
        "Site Processor Power (W)"
    )

    ax.set_title(
        "Green DISTRI — Site Processor Power Trace"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    fig.tight_layout()

    png_path = (
        output_dir
        / "site_power_trace.png"
    )

    pdf_path = (
        output_dir
        / "site_power_trace.pdf"
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

    return png_path, pdf_path


def plot_processor_activity(
    processor_metrics_path,
    output_dir,
):
    """
    Plot compute activity percentage for each processor.
    """

    rows = read_csv(
        processor_metrics_path
    )

    if not rows:
        raise ValueError(
            "processor_activity_metrics.csv "
            "contains no data."
        )

    processor_labels = [
        f"P{row['processor_id']}"
        for row in rows
    ]

    activity_percent = [
        float(row["activity_percent"])
        for row in rows
    ]

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    bars = ax.bar(
        processor_labels,
        activity_percent,
    )

    ax.set_xlabel(
        "Processor"
    )

    ax.set_ylabel(
        "Compute Activity (%)"
    )

    ax.set_title(
        "Green DISTRI — Processor Compute Activity"
    )

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    for bar, value in zip(
        bars,
        activity_percent,
    ):
        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()

    png_path = (
        output_dir
        / "processor_activity.png"
    )

    pdf_path = (
        output_dir
        / "processor_activity.pdf"
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

    return png_path, pdf_path


def plot_energy_breakdown(
    site_energy_summary_path,
    output_dir,
):
    """
    Plot idle baseline energy and activity-related
    incremental energy.
    """

    rows = read_csv(
        site_energy_summary_path
    )

    if not rows:
        raise ValueError(
            "site_energy_summary.csv "
            "contains no data."
        )

    row = rows[0]

    idle_energy = float(
        row["baseline_idle_energy_wh"]
    )

    activity_energy = float(
        row["activity_increment_energy_wh"]
    )

    total_energy = float(
        row["total_energy_wh"]
    )

    categories = [
        "Idle Baseline",
        "Compute Activity",
    ]

    values = [
        idle_energy,
        activity_energy,
    ]

    fig, ax = plt.subplots(
        figsize=(7, 5)
    )

    bars = ax.bar(
        categories,
        values,
    )

    ax.set_ylabel(
        "Energy (Wh)"
    )

    ax.set_title(
        "Green DISTRI — Processor Energy Breakdown"
    )

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    for bar, value in zip(
        bars,
        values,
    ):
        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f} Wh",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.text(
        0.5,
        0.95,
        f"Total Energy = {total_energy:.2f} Wh",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=10,
    )

    fig.tight_layout()

    png_path = (
        output_dir
        / "energy_breakdown.png"
    )

    pdf_path = (
        output_dir
        / "energy_breakdown.pdf"
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

    return png_path, pdf_path


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate Green DISTRI MVP plots."
        )
    )

    parser.add_argument(
        "--gdcs-dir",
        required=True,
        help=(
            "Directory containing Green DISTRI "
            "CSV results."
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory for generated plots. "
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

    site_power_trace_path = (
        gdcs_dir
        / "site_power_trace.csv"
    )

    processor_metrics_path = (
        gdcs_dir
        / "processor_activity_metrics.csv"
    )

    site_energy_summary_path = (
        gdcs_dir
        / "site_energy_summary.csv"
    )

    print()
    print(
        "Generating Green DISTRI plots..."
    )
    print("=" * 60)

    power_png, power_pdf = (
        plot_site_power_trace(
            site_power_trace_path,
            output_dir,
        )
    )

    activity_png, activity_pdf = (
        plot_processor_activity(
            processor_metrics_path,
            output_dir,
        )
    )

    energy_png, energy_pdf = (
        plot_energy_breakdown(
            site_energy_summary_path,
            output_dir,
        )
    )

    print(
        f"Site power trace:\n"
        f"  {power_png}\n"
        f"  {power_pdf}"
    )

    print()

    print(
        f"Processor activity:\n"
        f"  {activity_png}\n"
        f"  {activity_pdf}"
    )

    print()

    print(
        f"Energy breakdown:\n"
        f"  {energy_png}\n"
        f"  {energy_pdf}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()