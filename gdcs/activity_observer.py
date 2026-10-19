import csv
from pathlib import Path


class ActivityObserver:
    """
    Passive observer for Green DISTRI.

    Records simulation activity without changing
    scheduling or simulation timing.
    """

    FIELDNAMES = [
        "sim_time",
        "event",
        "site_id",
        "processor_id",
        "job_id",
        "job_category",
        "computation",
        "data_volume",
    ]

    def __init__(self):
        self.events = []

    def record(
        self,
        sim_time,
        event,
        site_id,
        processor_id,
        job,
    ):
        self.events.append(
            {
                "sim_time": sim_time,
                "event": event,
                "site_id": site_id,
                "processor_id": processor_id,
                "job_id": job.id,
                "job_category": job.category,
                "computation": job.computation,
                "data_volume": job.data_volume,
            }
        )

    def write_csv(self, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="") as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=self.FIELDNAMES,
            )

            writer.writeheader()
            writer.writerows(self.events)