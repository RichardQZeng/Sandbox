"""Concurrent read-process-write example"""

import concurrent.futures
from itertools import islice
from time import sleep

import rasterio


CHUNK = 100


def compute(path, window):
    """Simulates an expensive computation

    Gets source data for a window, sleeps, reverses bands.

    Note: Numpy ufuncs release GIL and are parallelizable.

    """
    # Uncomment this line to see interleaving of reading and writing.
    # print(f"Processing data: window={window}")
    with rasterio.open(path) as src:
        data = src.read(window=window)
    sleep(0.05)
    return window, data[::-1]


def main(infile, outfile, max_workers=1):

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

        with rasterio.open(infile) as src:

            with rasterio.open(outfile, "w", **src.profile) as dst:

                windows = (window for ij, window in dst.block_windows())
                group = islice(windows, CHUNK)
                futures = {executor.submit(compute, infile, window) for window in group}

                while futures:

                    done, futures = concurrent.futures.wait(
                        futures, return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    for future in done:
                        window, data = future.result()
                        # Uncomment this line to see interleaving of reading and writing.
                        # print(f"Writing data: window={window}")
                        dst.write(data, window=window)

                    group = islice(windows, CHUNK)

                    for window in group:
                        futures.add(executor.submit(compute, infile, window))


if __name__ == "__main__":
    import sys

    infile, outfile, num = sys.argv[1:4]
    main(infile, outfile, max_workers=int(num))

# run in IPython
# infile = r'd:/temp/RGB.byte.tif'
# outfile = r'd:/temp/test.tif'
# num = 1
# time main(infile, outfile, max_workers=int(num))
