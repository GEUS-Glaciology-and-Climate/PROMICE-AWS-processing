#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 9 13:44:49 2021
Major modifications: Oct 2022

@author: pho, pajwr

Functions for converting PROMICE .csv files to WMO-compliant BUFR files
Imported by pypromice/bin/getBUFR

This script uses the package eccodes to run. 
https://confluence.ecmwf.int/display/ECC/ecCodes+installation
Eccodes is the official package for WMO BUFR file construction. Eccodes must 
be configured on your computer BEFORE downloading the eccodes python bindings.
Eccodes can be configured with the conda python bindings, using the command
'conda install eccodes', however this didn't seem to work for me. Instead, I 
built eccodes separately and then installed the python bindings using pip3.
 
See here for a step-by-step guide on the eccodes set-up:
https://gist.github.com/MHBalsmeier/a01ad4e07ecf467c90fad2ac7719844a

Processing steps based on this example:
https://confluence.ecmwf.int/display/UDOC/How+do+I+create+BUFR+from+a+CSV+-+ecCodes+BUFR+FAQ
"""
import pandas as pd
import sys, traceback
from datetime import datetime, timedelta
from eccodes import codes_set, codes_write, codes_release, \
                    codes_bufr_new_from_samples, CodesInternalError, \
                    codes_is_defined
import math
import numpy as np
from sklearn.linear_model import LinearRegression

from pypromice.postprocess.wmo_config import ibufr_settings, stid_to_skip

# from IPython import embed

# To suppress pandas SettingWithCopyWarning
pd.options.mode.chained_assignment = None # default='warn'

#------------------------------------------------------------------------------

def getBUFR(s1, outBUFR, stid, land_stids):
    '''Construct and export .bufr messages to file from Series or DataFrame.
    PRIMARY DRIVER FUNCTION

    Parameters
    ----------
    s1 : pandas.Series
        Pandas series of single most recent obset for a station
    outBUFR : str
        File path that .bufr file will be exported to
    stid : str
        The station ID to be processed. e.g. 'KPC_U'
    land_stids : list
        List of station IDs for land-based stations
    '''
    # Open bufr file
    fout = open(outBUFR, 'wb')

    # for i1, r1 in df1.iterrows(): # If dataframe passed w/ multiple rows

    #Create new bufr message to write to
    ibufr = codes_bufr_new_from_samples('BUFR4')
    timestamp = datetime.strptime(s1['time'], '%Y-%m-%d %H:%M:%S')
    config_key = 'mobile'
    if stid in land_stids:
        config_key = 'land'
    try:
        setTemplate(ibufr, timestamp, stid, config_key)
        setStation(ibufr, stid, config_key)
        setAWSvariables(ibufr, s1, timestamp)

        #Encode keys in data section
        codes_set(ibufr, 'pack', 1)

        #Write bufr message to bufr file
        codes_write(ibufr, fout)

    except CodesInternalError as ec:
        print(traceback.format_exc())
        print(ec)
        sys.exit('-----> CodesInternalError in getBUFR!')
    except Exception as e:
        # Catch anything else here...
        print(traceback.format_exc())
        print(e)
        sys.exit('!!!!!!!!!! ERROR in getBUFR')

    codes_release(ibufr)

    fout.close()


def setTemplate(ibufr, timestamp, stid, config_key):
    '''Set bufr message template.

    Parameters
    ----------
    ibufr : bufr.msg
        Bufr message object
    timestamp : datetime.Datetime
        Timestamp of observation
    stid : str
        The station ID to be processed. e.g. 'KPC_U'
    config_key : str
        Defines which config dict to use in wmo_config.ibufr_settings, 'mobile' or 'land'
    '''
    for k, v in ibufr_settings[config_key]['template'].items():
        if codes_is_defined(ibufr, k) == 1:
            codes_set(ibufr, k, v)
        else:
            print('-----> setTemplate Key not defined: {}'.format(k))
            continue

    codes_set(ibufr, 'typicalYear', timestamp.year)
    codes_set(ibufr, 'typicalMonth', timestamp.month)
    codes_set(ibufr, 'typicalDay', timestamp.day)
    codes_set(ibufr, 'typicalHour', timestamp.hour)
    codes_set(ibufr, 'typicalMinute', timestamp.minute)
    # codes_set(ibufr, 'typicalSecond', timestamp.second)


def setStation(ibufr, stid, config_key):
    '''Set station-specific info to bufr message.

    Parameters
    ----------
    ibufr : bufr.msg
        Bufr message object
    stid : str
        The station ID to be processed. e.g. 'KPC_U'
    config_key : str
        Defines which config dict to use in wmo_config.ibufr_settings, 'mobile' or 'land'
    '''
    station_indentifier_keys = ('shipOrMobileLandStationIdentifier','stationNumber')
    for k, v in ibufr_settings[config_key]['station'].items():
        if k in station_indentifier_keys:
            # Deal with any string replacement of stid names before indexing
            if ('v3' in stid) and (stid.replace('v3','') in stid_to_skip['use_v3']):
                # We are reading the v3 station ID file, and the config says to use it!
                # But we need to write to BUFR without v3 name
                stid = stid.replace('v3','')
                # print('REPLACED!',stid)
            if stid == 'THU_U2':
                stid = 'THU_U'
                # print('REPLACED!',stid)
            if stid in ('JAR_O','SWC_O'):
                stid = stid.replace('_O','')
            if stid in v:
                codes_set(ibufr, k, v[stid])
            else:
                sys.exit('!!!!!!!!!! ID not found for {}'.format(stid))
        else:
            if codes_is_defined(ibufr, k) == 1:
                codes_set(ibufr, k, v)
            else:
               print('-----> setStation Key not defined: {}'.format(k))
               continue


def setAWSvariables(ibufr, row, timestamp):
    '''Set AWS measurements to bufr message.
    
    Parameters
    ----------
    ibufr : bufr.msg
        Bufr message object
    row : pandas.DataFrame row, or pandas.Series
        DataFrame row (or Series) with AWS variable data
    timestamp : datetime.datetime
        timestamp for this row
    '''
    setBUFRvalue(ibufr, 'year', timestamp.year)
    setBUFRvalue(ibufr, 'month', timestamp.month)
    setBUFRvalue(ibufr, 'day', timestamp.day)
    setBUFRvalue(ibufr, 'hour', timestamp.hour)
    setBUFRvalue(ibufr, 'minute', timestamp.minute)

    setBUFRvalue(ibufr, 'relativeHumidity', row['rh_i']) # DMI wants non-corrected
    setBUFRvalue(ibufr, 'airTemperature', row['t_i'])
    setBUFRvalue(ibufr, 'pressure', row['p_i'])
    setBUFRvalue(ibufr, 'windDirection', row['wdir_i'])
    setBUFRvalue(ibufr, 'windSpeed', row['wspd_i'])

    setBUFRvalue(ibufr, 'latitude', row['gps_lat_fit'])
    setBUFRvalue(ibufr, 'longitude', row['gps_lon_fit'])
    setBUFRvalue(ibufr, 'heightOfStationGroundAboveMeanSeaLevel', row['gps_alt_fit']) # also height and heightOfStation?

    # The ## in the codes_set() indicate the position in the BUFR for the parameter.
    # e.g. #10#timePeriod will assign to the 10th occurence of "timePeriod".
    # In the case of the synopMobil template, the 10th occurence is the wind speed section.
    # View the output BUFR to see section keys with 'bufr_dump filename.bufr'.
    if math.isnan(row['wspd_i']) is False:
        #Set time significance (2=temporally averaged)
        codes_set(ibufr, '#1#timeSignificance', 2)
        #Set monitoring time period (-10=10 minutes)
        codes_set(ibufr, '#10#timePeriod', -10)

    #Set measurement heights
    if math.isnan(row['z_boom_u_smooth']) is False:
        codes_set(ibufr,
                  '#1#heightOfSensorAboveLocalGroundOrDeckOfMarinePlatform',
                  row['z_boom_u_smooth']-0.1) # For air temp and RH
        codes_set(ibufr,
                  '#7#heightOfSensorAboveLocalGroundOrDeckOfMarinePlatform',
                  row['z_boom_u_smooth']+0.4) # For wind speed
        if math.isnan(row['gps_alt_fit']) is False:
            codes_set(ibufr, 'heightOfBarometerAboveMeanSeaLevel',
                      row['gps_alt_fit']+row['z_boom_u_smooth']) # For pressure


def setBUFRvalue(ibufr, b_name, value):
    '''Set variable in BUFR message
    Called in setAWSvariables() to make sure we aren't passing NaNs

    Parameters
    ----------
    ibufr : bufr.msg                
        Active BUFR message
    b_name : str
        BUFR message variable name
    value : int/float
        Value to be assigned to variable
    '''
    if math.isnan(value) is False:
        try:
            codes_set(ibufr, b_name, value)
        except CodesInternalError as ec:
            print(f'{ec}: {b_name}')
            sys.exit('-----> CodesInternalError in setBUFRvalue!')
    else:
        print('----> {} {}'.format(b_name, value))


def linear_fit(df, column, decimals, stid):
    '''Apply a linear regression to the input column

    Parameters
    ----------
    df : pandas.Dataframe
        datetime-indexed df, limited to desired time length for linear fit
    column : str
        The target column for applying linear fit
    decimals : int
        How many decimals to round the output fit values
    stid : str
        The station ID to be processed. e.g. 'KPC_U'

    Returns
    -------
    df : pandas.Dataframe
        The original input df, with added column for the linear regression values

    Linear regression is following:
    https://realpython.com/linear-regression-in-python/#simple-linear-regression-with-scikit-learn
    '''
    if column in df:
        df_dropna = df[df[column].notna()] # limit to only non-nan for the target column
        if len(df_dropna[column]) > 0:
            # Get datetime x values into epoch sec integers
            x_epoch = df_dropna.index.values.astype(np.int64) // 10 ** 9
            x = x_epoch.reshape(-1,1)
            y = df_dropna[column].values # can also reshape this, but not necessary
            model = LinearRegression().fit(x, y)
            y_pred = model.predict(x).round(decimals=decimals)

            # Plot data if desired
            # if stid == 'LYN_T':
            #     if (column == 'gps_lat') or (column == 'gps_lon') or (column == 'gps_alt'):
            #         import matplotlib.pyplot as plt
            #         plt.scatter(x,y)
            #         plt.plot(x,y_pred, color='red')
            #         plt.title('{} {}'.format(stid, column))
            #         plt.show()

            # Add y_pred back to original df
            df_dropna['y_pred'] = y_pred
            df['{}_fit'.format(column)] = df_dropna['y_pred']
        else:
            # All data is NaN! Just write NaNs using the original column
            print('----> No {} data for {}!'.format(column, stid))
            df['{}_fit'.format(column)] = df[column]
    else:
        print('----> {} not found in dataframe!'.format(column))
        pass

    return df


def rolling_window(df, column, window, min_periods, decimals):
    '''Apply a rolling window (smoothing) to the input column

    Parameters
    ----------
    df : pandas.Dataframe
        datetime-indexed df
    column : str
        The target column for applying rolling window
    window : str
        Window size (e.g. '24H' or 30D')
    min_periods : int
        Minimum number of observations in window required to have a value;
        otherwise, result is np.nan.
    decimals : int
        How many decimal places to round the output smoothed values

    Returns
    -------
    df : pandas.Dataframe
        The original input df, with added column for the smoothed values
    '''
    df['{}_smooth'.format(column)] = df[column].rolling(
        window,
        min_periods=min_periods,
        center=True, # set the window labels as the center of the window
        closed='both' # no points in the window are excluded (first or last)
        ).median().round(decimals=decimals) # could also round to whole meters (decimals=0)
    return df

def round_values(s):
    '''Enforce precision
    Note the sensor accuracies listed here:
    https://essd.copernicus.org/articles/13/3819/2021/#section8
    In addition to sensor accuracy, WMO requires pressure and heights
    to be reported at 0.1 precision.
    
    Parameters
    ----------
    s : pandas series (could also be a dataframe)

    Returns
    -------
    s : modified pandas series (could also be a dataframe)
    '''
    s['rh_i'] = s['rh_i'].round(decimals=0)
    s['wspd_i'] = s['wspd_i'].round(decimals=1)
    s['wdir_i'] = s['wdir_i'].round(decimals=0)
    s['t_i'] = s['t_i'].round(decimals=1)
    s['p_i'] = s['p_i'].round(decimals=1)

    # gps_lat,gps_lon,gps_alt,z_boom_u are all rounded in linear_fit() or rolling_window()
    return s

def write_positions(s, stid, positions):
    '''Set valid lat, lon, alt to the positions dict.
    Find recent position metadata for submitting to DMI/WMO.
    Not used in production! Must pass --positions arg.

    Parameters
    ----------
    s : pandas series
        The current obset we are working with (for BUFR submission)
    stid : str
        The station ID, such as NUK_L
    positions : dict
        Dict storing current station positions.

    Returns
    -------
    positions : dict
        Modified dict storing current station positions.
    '''
    to_write = ['lat','lon']
    for i in to_write:
        if (f'gps_{i}_fit' in s) and (pd.isna(s[f'gps_{i}_fit']) is False):
            positions[stid][i] = s[f'gps_{i}_fit']

    # Add altitude to positions dict:
    if ('gps_alt_fit' in s) and (pd.isna(s['gps_alt_fit']) is False):
        positions[stid]['alt'] = s['gps_alt_fit']

    # Add timestamp
    positions[stid]['timestamp'] = s['time']
    return positions

def fetch_old_positions(df, stid, time_limit, positions):
    '''Set valid lat, lon, alt to the positions dict.
    Used to find "old" GPS positions for submitting position metadata to DMI/WMO,
    and for writing positions to AWS_station_locations.csv for skipped or rejected stations.

    Parameters
    ----------
    df : pandas dataframe
        The full tx dataframe
    stid : str
        The station ID, such as NUK_L
    time_limit : str
        Previous time to limit dataframe before applying linear regression.
        (e.g. '3M')
    positions : dict
        Dict storing current station positions.

    Returns
    -------
    positions : dict
        Modified dict storing current station positions.
    '''
    # Combine gps and msg lat and lon using combine_first()
    # If any GPS positions are missing, we will fill the missing GPS positions with modem
    # positions (if they are present). Important to do this first, and then apply linear fit
    # to the resulting single array. Otherwise, we can have jumps when the GPS data goes out
    # or comes back. The message coordinates can sometimes all be 0.0, so we check for this.

    df_limited = df.last(time_limit)

    if ('msg_lat' in df_limited) and ('msg_lon' in df_limited):
        if (0.0 not in df_limited['msg_lat'].values):
            df_limited['gps_lat'] = df_limited['gps_lat'].combine_first(df_limited['msg_lat'])
        if (0.0 not in df_limited['msg_lon'].values):
            df_limited['gps_lon'] = df_limited['gps_lon'].combine_first(df_limited['msg_lon'])

    # Find valid GPS data
    valid_gps = df_limited.dropna(subset=['gps_lat','gps_lon','gps_alt'])

    if valid_gps.empty is False:
        valid_gps = linear_fit(valid_gps, 'gps_alt', 1, stid)
        valid_gps = linear_fit(valid_gps, 'gps_lat', 6, stid)
        valid_gps = linear_fit(valid_gps, 'gps_lon', 6, stid)

        s = valid_gps.loc[valid_gps.index.max()]

        to_write = ['lat','lon']
        for i in to_write:
            if (f'gps_{i}_fit' in s) and (pd.isna(s[f'gps_{i}_fit']) is False):
                positions[stid][i] = s[f'gps_{i}_fit']
                # positions[stid][f'{i}_source'] = 'OLD' #source flag

        # Add altitude to positions dict:
        if ('gps_alt_fit' in s) and (pd.isna(s['gps_alt_fit']) is False):
            positions[stid]['alt'] = s['gps_alt_fit']

        # Add timestamp
        positions[stid]['timestamp'] = s['time']
    return positions


def min_data_check(s, stid):
    '''Check that we have minimum required fields to proceed with writing to BUFR

    Parameters
    ----------
    s : pandas series
        The current obset we are working with (for BUFR submission)
    stid : str
        The station ID, such as NUK_L

    Returns
    -------
    min_data_wx_result : bool
        True (default), the test for min wx data passed. False, the test failed.
    min_data_pos_result : bool
        True (default), the test for min position data passed. False, the test failed.
    '''
    min_data_wx_result = True
    min_data_pos_result = True

    # Can use pd.isna() or math.isnan()
    # Must have valid air temp and pressure
    if (pd.isna(s['t_i']) is False) and (pd.isna(s['p_i']) is False):
        pass
    else:
        print('----> Failed min_data_check for air temp and pressure!')
        min_data_wx_result = False

    # Must have a valid position
    # Note that gps_ variables have already had replacement with msg_ positions if needed

    # Missing just elevation OK
    # if (pd.isna(s['gps_lat_fit']) is False) and (pd.isna(s['gps_lon_fit']) is False):
    #     pass
    # Require all three: lat, lon, elev
    if ((pd.isna(s['gps_lat_fit']) is False) and
        (pd.isna(s['gps_lon_fit']) is False) and
        (pd.isna(s['gps_alt_fit']) is False)):
        pass
    else:
        print('----> Failed min_data_check for position!')
        min_data_pos_result = False

    return min_data_wx_result, min_data_pos_result