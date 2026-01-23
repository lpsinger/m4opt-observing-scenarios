import numpy as np
from astropy import units as u
from astropy.table import QTable
from rate_stats import poisson_lognormal_rate_quantiles
from scipy import stats

runs = ["O5a", "O5b", "O5c"]

main_table = QTable.read("data/events.ecsv")

# Throw away events with objective value less than cutoff
plan_args = QTable.read(
    f"data/{main_table[0]['run']}/{main_table[0]['coinc_event_id']}.ecsv"
).meta["args"]
cutoff = plan_args["cutoff"]
main_table = main_table[main_table["objective_value"] >= cutoff]

is_class_by_category = {
    "BNS": lambda table: table["source_class"] == "BNS",
    "NSBH": lambda table: table["source_class"] == "NSBH",
    "All": lambda table: np.ones(len(table), dtype=bool),
}

tables_by_run = [main_table[main_table["run"] == run] for run in runs]
tables_by_run_and_class = [
    [table[is_class(table)] for is_class in is_class_by_category.values()]
    for table in tables_by_run
]

# Full astrophysical rate density for all mergers
# GWTC-4 paper (https://arxiv.org/pdf/2508.18083) Table 2 BPG, full cell
lo = 50
mid = 110
hi = 240

(standard_90pct_interval,) = np.diff(stats.norm.interval(0.9))
log_target_rate_mu = np.log(mid)
log_target_rate_sigma = np.log(hi / lo) / standard_90pct_interval
log_target_rate_mu, log_target_rate_sigma

log_simulation_effective_rate_by_run = [
    np.log(main_table.meta["effective_rate"][run].to_value(u.Gpc**-3 * u.yr**-1))
    for run in runs
]

prob_quantiles = np.asarray([0.5, 0.05, 0.95])
run_duration = 1.5  # years
mu = np.asarray(
    [
        [
            log_target_rate_mu
            + np.log(run_duration)
            - log_simulation_effective_rate
            + np.log(
                [
                    np.sum(_)
                    for _ in [
                        np.ones_like(table["objective_value"]),
                        table["detection_probability_known_position"],
                    ]
                ]
            )
            for table in tables
        ]
        for tables, log_simulation_effective_rate in zip(
            tables_by_run_and_class, log_simulation_effective_rate_by_run
        )
    ]
)

mu = np.moveaxis(mu, (0, 1, 2), (1, 2, 0))

rate_quantiles = poisson_lognormal_rate_quantiles(
    prob_quantiles[np.newaxis, np.newaxis, np.newaxis, :],
    mu[:, :, :, np.newaxis],
    log_target_rate_sigma,
)

with open("tables/selected-detected.tex", "w") as f:
    n_cats = len(is_class_by_category)
    cols = "r@{}l" * n_cats
    n_runs = len(runs)
    print(r"\begin{deluxetable*}{l" + f"|{cols}" * n_runs + "}", file=f)
    print(
        r"    \tablecaption{\label{tab:selected-detected}Expected Number of Events}",
        file=f,
    )
    print(r"    \tablehead{", file=f)
    print(
        r"       ",
        *(rf"\multicolumn{{{n_cats * 2}}}{{c}}{{{run}}}" for run in runs),
        sep=" & ",
        end=r" \\" "\n",
        file=f,
    )
    print(
        r"       ",
        *(
            rf"\multicolumn{{2}}{{c}}{{{class_}}}"
            for class_ in runs
            for class_ in is_class_by_category.keys()
        ),
        sep=" & ",
        file=f,
    )
    print(r"    }", file=f)
    print(r"    \startdata", file=f)
    for i, (label, by_run) in enumerate(
        zip(["Number of events selected", "Number of events detected"], rate_quantiles)
    ):
        print(f"    {label}", end="", file=f)
        for by_class in by_run:
            print(
                *(
                    " & {} & $_{{-{}}}^{{+{}}}$".format(
                        *np.rint([mid, mid - lo, hi - mid]).astype(int)
                    )
                    for mid, lo, hi in by_class
                ),
                sep="",
                end="",
                file=f,
            )
        if i < len(runs) - 1:
            print(r" \\", file=f)
        else:
            print(file=f)
    print(r"    \enddata", file=f)
    print(r"\end{deluxetable*}", file=f)
