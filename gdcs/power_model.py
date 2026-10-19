from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessorPowerModel:
    """
    Green DISTRI MVP processor power model.

    The current DISTRI compute model does not expose
    calibrated physical CPU utilization.

    Therefore, MVP v0.1 uses an activity-based utilization
    proxy:

        u(t) = 0  if no compute job is active
        u(t) = 1  if one or more compute jobs are active

    Power:

        P(t) = P_idle +
               (P_active - P_idle) * u(t)

    Units:
        power: watts (W)
    """

    idle_power_w: float
    active_power_w: float

    def __post_init__(self):

        if self.idle_power_w < 0:
            raise ValueError(
                "idle_power_w must be >= 0"
            )

        if self.active_power_w <= 0:
            raise ValueError(
                "active_power_w must be > 0"
            )

        if self.active_power_w < self.idle_power_w:
            raise ValueError(
                "active_power_w must be >= idle_power_w"
            )

    def utilization_proxy(
        self,
        active_jobs: int,
    ) -> float:
        """
        Return the activity-based utilization proxy.

        0.0 -> processor has no active compute job
        1.0 -> processor has at least one active compute job
        """

        if active_jobs < 0:
            raise ValueError(
                "active_jobs cannot be negative"
            )

        return (
            1.0
            if active_jobs > 0
            else 0.0
        )

    def power_w(
        self,
        active_jobs: int,
    ) -> float:
        """
        Return processor power in watts.
        """

        u = self.utilization_proxy(
            active_jobs
        )

        return (
            self.idle_power_w
            +
            (
                self.active_power_w
                - self.idle_power_w
            )
            * u
        )