from pathlib import Path

from detection_probability import get_detection_probability_known_position

base_path = Path("data")


def process(row):
    run = row["run"]
    event_id = row["coinc_event_id"]
    plan = QTable.read(base_path / run / f"{event_id}.ecsv")
    plan_args = {**plan.meta["args"]}
    plan_args.pop("skymap")
    return (
        get_detection_probability_known_position(plan, row, plan_args),
        plan.meta["objective_value"],
        plan.meta["best_bound"],
        plan.meta["solution_status"],
        plan.meta["solution_time"],
        len(plan[plan["action"] == "observe"]) // plan_args["visits"],
    )


if __name__ == "__main__":
    from astropy.table import QTable
    from ligo.skymap.util.progress import progress_map

    runs = ["O5", "O6"]

    # Read summary data for all events
    table = QTable.read(base_path / "observing-scenarios.ecsv")

    (
        table["detection_probability_known_position"],
        table["objective_value"],
        table["best_bound"],
        table["solution_status"],
        table["solution_time"],
        table["num_fields"],
    ) = zip(*progress_map(process, table, jobs=None))

    table.write(base_path / "events.ecsv", overwrite=True)
