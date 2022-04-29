# PROMICE-AWS-processing

## Table of contents   
+ [Example code](#example-code)
- [Command line](#Command-line)
- [Command line: parallelized](#command-line-parallelized)
- [Python](#python)
+ [Introduction](#introduction)
- [Overview](#overview)
+ [Level 0](#level-0)
- [L0 files](#l0-files)
- [Additional files](#additional-files)

## Example code

### Command line

```python
python promiceAWS.py --config_file=./test_data/L0/config/QAS_L.toml --data_dir=./test_data
ls ./test_data/L3/QAS_L
```

```python
: QAS_L_day.csv
: QAS_L_day.nc
: QAS_L_hour.csv
: QAS_L_hour.nc
```
 
### Command line: parallelized

```python
parallel --bar "python promiceAWS.py --config_file={1} --data_dir=./test_data" ::: $(ls ./test_data/L0/config/*)
ls ./test_data/L3/*/
```

```python
./test_data/L3/QAS_L/:
QAS_L_day.csv
QAS_L_day.nc
QAS_L_hour.csv
QAS_L_hour.nc

./test_data/L3/QAS_M/:
QAS_M_day.csv
QAS_M_day.nc
QAS_M_hour.csv
QAS_M_hour.nc

./test_data/L3/QAS_U/:
QAS_U_day.csv
QAS_U_day.nc
QAS_U_hour.csv
QAS_U_hour.nc
```

### Python

```python
from promiceAWS import promiceAWS
pAWS = promiceAWS(config_file='./test_data/L0/config/QAS_L.toml', data_dir='./test_data')
pAWS.process()
pAWS.write(data_dir='./test_data') # Saves L3 data 4x: Daily and hourly in both CSV and NetCDF format
```

## Introduction

Code used to process the PROMICE AWS data from Level 0 through Level 3 (end-user product).

Currently, this code focuses on the **transmitted** data.

We use the following processing levels, described textually and graphically.

### Overview
+ L0: Raw data in CSV file format in one of three formats:
- [ ] =raw= (see below)
- [ ] =STM= (Slim Table Memory; see below)
- [x] =TX= (transmitted; see below)
- Manually split so no file includes changed sensors, changed calibration parameters, etc.
- [x] Manually created paired header files based on [example (template) L0 config file](https://github.com/GEUS-Glaciology-and-Climate/PROMICE-AWS-processing/blob/main/example.toml) or in the `data/L0/config` folder.
+ L1:
- [x] Engineering units (e.g. current or volts) converted to physical units (e.g. temperature or wind speed)
+ L1A:
- [ ] Invalid / bad / suspicious data flagged
- [x] Files merged to one time series per station
+ L2:
- [x] Calibration using secondary sources (e.g. radiometric correction requires input of tilt sensor)
+ L3:
- [x] Derived products (e.g. SHF and LHF)
- [ ] Merged, patched, and filled (raw > STM > TX) to one product

<img src="https://github.com/GEUS-Glaciology-and-Climate/PROMICE-AWS-processing/blob/main/fig/levels.png?raw=true" width="1000" align="aligncenter">


## Level 0

Level 0 is generated from one of three methods:
+ [ ] Copied from CF card in the field
+ [ ] Downloaded from logger box in the field
+ [x] Transmitted via satellite and decoded by https://github.com/GEUS-Glaciology-and-Climate/awsrx

<img src="https://github.com/GEUS-Glaciology-and-Climate/PROMICE-AWS-processing/blob/main/fig/L00_to_L0.png?raw=true" width="1000" align="aligncenter">


### L0 files

+ `raw` : All 10-minute data stored on the CF-card (external module on CR logger)
+ `SlimTableMem` : Hourly averaged 10-min data stored in the internal logger memory
+ `transmitted` : Transmitted via satellite. Only a subset of data is transmitted, and only hourly or daily average depending on station and day of year.

Level 0 files are stored in the `data/L0/<S>/` folder, where `<S>` is the station name. File names can be anything are are processed as per the =TOML= config files, but ideally they should encode the station, end-of-year of download, a version number if there are multiple files for a given year, and the format. Best practices would use the following conventions:  

+ Generic: `data/<L>/<S>/<S>_<Y>[.<n>]_<F>.txt`
+ Example: `data/L0/QAS_L/QAS_L_2021_raw_transmitted.txt`

Where 

+ `<L>` is the processing level
  + `<L>` must be one of the following: [L0, L1, L1A, L2, L3]
+ `<S>` is a station ID
  + `<S>` must be one of the following strings: [CEN, EGP, KAN_B, KAN_L, KAN_M, KAN_U, KPC_L, KPC_U, MIT, NUK_K, NUK_L, NUK_N, NUK_U, QAS_A, QAS_L, QAS_M, QAS_U, SCO_L, SCO_U, TAS_A, TAS_L, TAS_U, THU_L, THU_U, UPE_L, UPE_U]
+ `<Y>` is a four-digit year with a value greater than `2008`
  + `<Y>` should represent the year at the last timestamp in the file
  + Optionally, `.<n>` is a version number if multiple files from the same year are present
+ `<F>` is the format, one of `raw`, `TX`, or `STM`

Each L0 file that will be processed must have an entry in the TOML-formatted configuration file. The config file can be located anywhere, and the processing script receives the config file and the location of the L0 data. An [example (template) L0 config file](https://github.com/GEUS-Glaciology-and-Climate/PROMICE-AWS-processing/blob/main/example.toml) is:

```bash
station_id         = "EGP"
latitude           = 75.62
longitude          = -35.98
nodata             = ['-999', 'NAN'] # if one is a string, all must be strings
dsr_eng_coef       = 12.71  # from manufacturer to convert from eng units (1E-5 V) to  physical units (W m-2)
usr_eng_coef       = 12.71
dlr_eng_coef       = 12.71
ulr_eng_coef       = 12.71

columns = ["time", "rec", "min_y",
	"p", "t_1", "t_2", "rh", "wspd", "wdir", "wd_std",
	"dsr", "usr", "dlr", "ulr", "t_rad",
	"z_boom", "z_boom_q", "z_stake", "z_stake_q", "z_pt",
	"t_i_1", "t_i_2", "t_i_3", "t_i_4", "t_i_5", "t_i_6", "t_i_7", "t_i_8",
	"tilt_x", "tilt_y",
	"gps_time", "gps_lat", "gps_lon", "gps_alt", "gps_geoid", "SKIP_34", "SKIP_35", "gps_numsat", "gps_hdop",
	"t_log", "fan_dc", "SKIP_40", "batt_v_ss", "batt_v"]

# Parameters applied to all files are above.
# Define files for processing and
# override file-specific parameters below.

["EGP_2016_raw.txt"]
format    = "raw"
skiprows  = 3
hygroclip_t_offset = 0      # degrees C

["EGP_2019_raw_transmitted.txt"]
hygroclip_t_offset = 0
skiprows = 0
format   = "TX"
columns = ["time", "rec",
	"p", "t_1", "t_2", "rh", "wspd", "wdir",
	"dsr", "usr", "dlr", "ulr", "t_rad",
	"z_boom", "z_stake", "z_pt",
	"t_i_1", "t_i_2", "t_i_3", "t_i_4", "t_i_5", "t_i_6", "t_i_7", "t_i_8",
	"tilt_x", "tilt_y",
	"gps_time", "gps_lat", "gps_lon", "gps_alt", "gps_hdop",
	"fan_dc", "batt_v"]
```

The TOML config file has the following expectations and behaviors:
+ Properties can be defined at the top level or under a section
+ Each file that will be processed gets its own section
+ Properties at the top level are copied to each section (assumed to apply to all files)
+ Top-level properties are overridden by file-level properties if they exist in both locations

In the example above,
+ The `station_id`, `latitude`, etc. properties are the same in both files (`EGP_2016_raw.txt` and `EGP_2019_raw_transmitted.txt`) and so they are defined once at the top of the file. They could have been defined in each of the sections similar to `hygroclip_t_offset`.
+ The `format` and `skiprows` properties are different in each section and defined in each section
+ The top-level defined `columns` is applied only to `EGP_2016_raw.txt` because it is defined differently in the `EGP_2019_raw_transmitted.txt` section.

### Additional files

Any files that do not have an associated section in the config file will be ignored. However, for cleanliness, L0 files that will not be processed should be placed in an `L0/<S>/archive` subfolder.

Any changes made to L0 files should be documented. **Manual changes to these files should only be done when necessary**. An example of a manual change might be:

+ Raw file contains multiple years of data, including replacing sensors that have different calibration units. The file should be split so that each file only contains one version of each sensor (assuming different versions need different metadata).

