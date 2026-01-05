#!/usr/bin/env python
# fmt: off
#SBATCH --partition=shared
#SBATCH --account=umn131
#SBATCH -N1 -n1 --mem 8G
#SBATCH -t 08:00:00
# fmt: on
"""Run the M4OPT scheduler on a batch of sky maps on the SDSC Expanse cluster
(https://www.sdsc.edu/services/hpc/expanse/)."""

job_cpu = 8
run = "O5"
event_id = 800


def task(exptime_s):
    import shlex

    from m4opt._cli import app

    cmdline = f"schedule --mission=uvex --bandpass=FUV --deadline=6hour --timelimit=2hour --memory=10GiB --exptime-min={exptime_s}s --nside=128 --jobs={job_cpu} data/{run}/{event_id}.fits data/{run}/{event_id}-exptime-{exptime_s}s.ecsv"
    args = shlex.split(cmdline)
    print(cmdline)
    try:
        app(args)
    except SystemExit as e:
        if e.code != 0:
            raise RuntimeError(f"Process exited with code {e.code}")


if __name__ == "__main__":
    from dask_jobqueue import SLURMCluster
    from distributed import as_completed
    from tqdm.auto import tqdm

    walltime = 8 * 60
    max_workers = 64
    exptime_s = list(range(300, 3700, 100))

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
            as_completed(client.map(task, exptime_s)), total=len(exptime_s)
        ):
            future.result()
