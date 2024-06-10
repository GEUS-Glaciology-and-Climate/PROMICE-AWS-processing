#!/usr/bin/env python
import os, logging, sys
import xarray as xr
from argparse import ArgumentParser
import pypromice
from pypromice.process.load import getVars, getMeta
from pypromice.process.L2toL3 import toL3
from pypromice.process.write import prepare_and_write

def parse_arguments_l2tol3(debug_args=None):
    parser = ArgumentParser(description="AWS L3 script for the processing L3 "+
                            "data from L2 and merging the L3 data with its "+
                            "historical site. An hourly, daily and monthly L3 "+
                            "data product is outputted to the defined output path")
    parser.add_argument('-i', '--inpath', type=str, required=True, 
                        help='Path to Level 2 .nc data file')
    parser.add_argument('-o', '--outpath', default=None, type=str, required=False, 
                        help='Path where to write output')
    parser.add_argument('-v', '--variables', default=None, type=str, 
                        required=False, help='File path to variables look-up table')
    parser.add_argument('-m', '--metadata', default=None, type=str, 
                        required=False, help='File path to metadata')
    parser.add_argument('-t', '--time', default='60min', type=str, 
                        required=False, help='Time interval to resample dataset. The default is "60min"')
    parser.add_argument('-g', '--gcnet_historical', default=None, type=str, 
                        required=False, help='File path to historical GC-Net data file')

    # here will come additional arguments for the merging with historical stations
    args = parser.parse_args(args=debug_args)
    return args

def get_l2tol3():
    args = parse_arguments_l2tol3()
    logging.basicConfig(
        format="%(asctime)s; %(levelname)s; %(name)s; %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )

    # Define variables and metadata (either from file or pypromice package defaults)
    v = getVars(args.variables)
    m = getMeta(args.metadata)
  
    # Define Level 2 dataset from file
    l2 = xr.open_dataset(args.inpath)
    
    # Perform Level 3 processing
    l3 = toL3(l2)
    
    # Write Level 3 dataset to file if output directory given
    if args.outpath is not None:
        prepare_and_write(l3, args.outpath, v, m, args.time)

if __name__ == "__main__":  
    get_l2tol3()
