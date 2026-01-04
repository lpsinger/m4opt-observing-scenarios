"""Unpack just the data that we need from https://zenodo.org/records/14585837."""

import pathlib
import sqlite3
import zipfile
from functools import reduce
from shutil import copyfileobj
from tempfile import NamedTemporaryFile

from astropy import units as u
from astropy.cosmology import Planck15 as cosmo
from astropy.cosmology import z_at_value
from astropy.table import QTable, join, vstack
from tqdm.auto import tqdm

runs = ["O5a", "O5b", "O5c"]
out_root = pathlib.Path("data")

for run in runs:
    (out_root / run).mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile("runs.zip") as archive:
    in_root = zipfile.Path(archive) / "runs"

    # Read summary tables, join together
    tables = []
    for run in tqdm(runs, desc="Reading summary tables"):
        in_run = in_root / run / "bgp"
        table = reduce(
            join,
            (
                (
                    QTable.read((in_run / filename).read_text(), format="ascii")
                    for filename in ["coincs.dat", "allsky.dat", "injections.dat"]
                )
            ),
        )

        table["run"] = run

        table.meta.clear()

        with (
            (in_run / "events.sqlite").open("rb") as in_file,
            NamedTemporaryFile() as out_file,
        ):
            copyfileobj(in_file, out_file)
            out_file.flush()
            with sqlite3.connect(f"file:{out_file.name}?mode=ro", uri=True) as db:
                ((comment,),) = db.execute(
                    "SELECT comment FROM process WHERE program = 'bayestar-inject'"
                )
        table.meta["effective_rate"] = {run: u.Quantity(comment)}

        tables.append(table)

    table = vstack(tables)
    del tables

    # Keep only NSBH/BNS events
    z = z_at_value(cosmo.luminosity_distance, table["distance"] * u.Mpc).to_value(
        u.dimensionless_unscaled
    )
    max_mass2 = 2.5
    table = table[table["mass2"] <= max_mass2 * (1 + z)]

    table.write(out_root / "observing-scenarios.ecsv", overwrite=True)

    # Copy FITS files
    for row in tqdm(table, desc="Copying FITS files"):
        filename = f"{row['coinc_event_id']}.fits"
        in_path = in_root / row["run"] / "bgp" / "allsky" / filename
        out_path = out_root / row["run"] / filename
        with in_path.open("rb") as in_file, out_path.open("wb") as out_file:
            copyfileobj(in_file, out_file)
