#!/usr/bin/env python
# fmt: off
#SBATCH --partition=shared
#SBATCH --account=umn131
#SBATCH -N1 -n1 --mem 8G
#SBATCH -t 12:00:00
# fmt: on
"""Run the M4OPT scheduler on a batch of sky maps on the SDSC Expanse cluster
(https://www.sdsc.edu/services/hpc/expanse/)."""

job_cpu = 8


def task(run, event_id):
    import shlex

    from m4opt._cli import app

    cmdline = f"schedule --mission=uvex --bandpass=NUV --deadline=6hour --timelimit=2hour --memory=10GiB --absmag-mean=-15.1 --absmag-stdev=1.6 --exptime-min=300s --nside=128 --cutoff=0.1 --jobs={job_cpu} data/{run}/{event_id}.fits data/{run}/{event_id}.ecsv"
    args = shlex.split(cmdline)
    print(cmdline)
    try:
        app(args)
    except SystemExit as e:
        if e.code != 0:
            raise RuntimeError(f"Process exited with code {e.code}")


if __name__ == "__main__":
    from astropy.table import QTable
    from dask_jobqueue import SLURMCluster
    from distributed import as_completed
    from tqdm.auto import tqdm

    table = QTable.read("data/observing-scenarios.ecsv")

    walltime = 12 * 60
    max_workers = 512

    with (
        SLURMCluster(
            account="umn131",
            cores=1,
            job_cpu=job_cpu,
            job_extra_directives=["--nodes=1"],
            job_script_prologue=[f"export OMP_NUM_THREADS={job_cpu}"],
            memory="16GiB",
            processes=1,
            queue="shared",
            walltime=str(walltime),
            worker_extra_args=[
                "--lifetime",
                f"{walltime - 5}m",
                "--lifetime-stagger",
                "4m",
            ],
        ) as cluster,
        cluster.get_client() as client,
    ):
        print("Submit script:")
        print(cluster.job_script())
        print("Dashboard link:", cluster.dashboard_link)
        cluster.adapt(maximum=max_workers)
        for future in tqdm(
            as_completed(
                client.map(
                    task, table["run"].tolist(), table["coinc_event_id"].tolist()
                )
            ),
            total=len(table),
        ):
            future.result()
