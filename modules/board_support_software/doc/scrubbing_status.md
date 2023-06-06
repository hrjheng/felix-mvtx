# A Scrubbing Status Primer

The scrubbing status software keep track of current status and statistics of various block addresses on the 2 Flash IC's on the RUs.
The scrubbing status files are stored in ~/ITS_scrubbing_status/<RU_SN>.json

## Create status files

To use the features one first needs to create status files.

```
./testbench_<>.py rdo create_and_store_new_scrubbing_status
```

By default, it creates locations defined only in page 0. However with the `--clear_scrub_block_address` flag, it will create locations with all possible locations (following PA3 fw v2.0D).
Note that the page 0 locations will be assumed to be already programmed and OK. The locations from `clear_scrub_block_address` will be needed to be programmed (see next section).

## Programming

### Not programmed

We can automatically program all locations which have status `NOT_PROGRAMMED`:

```
./testbench_<>.py rdo flash_all_not_programmed_locations <FILENAME BS ECC BITFILE>
```
Following the program, each location will be tested and automatically given a status.

### Critical

We can automatically reprogram all locations which have status `CRITICAL`:

```
./testbench_<>.py rdo reflash_all_critical_locations <FILENAME BS ECC BITFILE>
```

NOTE: This procedure is different than previous one also in how the stats are updated.

## Check all locations

We can iterate over all locations and check their current behavior. Convenient when its been a long time since programming and we want to check whether radiation has impacted block.

```
./testbench_<>.py rdo check_and_update_scrub_status_iter_locations
```

## Scrubbing loop

To run an automated loop:

```
./testbench_<>.py rdo run_scrub_loop --sleep_sec=10
```

Upon errors, the next good block is selected automatically.