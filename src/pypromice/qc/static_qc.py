import numpy as np
import pandas as pd
import xarray as xr


def staticQC(ds: xr.Dataset) -> xr.Dataset:
    '''
    Detect and filter data points that sems to be static within a certain period.

    TODO: It could be nice to have a reference to the logger or description of the behaviour here.
    The AWS logger program is know to return the last successfully read value if it fails reading from the sensor.

    Parameters
    ----------
    ds : xr.Dataset
         Level 1 datset

    Returns
    -------
    ds_out : xr.Dataset
            Level 1 dataset with difference outliers set to NaN
    '''

    # the differenceQC is not done on the Windspeed
    # Optionally examine flagged data by setting make_plots to True
    # This is best done by running aws.py directly and setting 'test_station'
    # Plots will be shown before and after flag removal for each var

    df = ds.to_dataframe()  # Switch to pandas

    # Define threshold dict to hold limit values, and the difference values.
    # Limit values indicate how much a variable has to change to the previous value
    # diff_period is how many hours a value can stay the same without being set to NaN
    # * are used to calculate and define all limits, which are then applied to *_u, *_l and *_i

    var_threshold = {
        't': {'static_limit': 0.001, 'diff_period': 1},
        'p': {'static_limit': 0.0001, 'diff_period': 24},
        'rh': {'static_limit': 0.0001, 'diff_period': 24}
    }

    for k in var_threshold.keys():

        var_all = [k + '_u', k + '_l', k + '_i']  # apply to upper, lower boom, and instant
        static_limit = var_threshold[k]['static_limit']  # loading static limit
        diff_period = var_threshold[k]['diff_period']  # loading diff period

        for v in var_all:
            if v in df:
                mask = find_static_regions(df[v], diff_period, static_limit)
                # setting outliers to NaN
                df.loc[mask, v] = np.nan

    # Back to xarray, and re-assign the original attrs
    ds_out = df.to_xarray()
    ds_out = ds_out.assign_attrs(ds.attrs)  # Dataset attrs
    for x in ds_out.data_vars:  # variable-specific attrs
        ds_out[x].attrs = ds[x].attrs
    # equivalent to above:
    # vals = [xr.DataArray(data=df_out[c], dims=['time'], coords={'time':df_out.index}, attrs=ds[c].attrs) for c in df_out.columns]
    # ds_out = xr.Dataset(dict(zip(df_out.columns, vals)), attrs=ds.attrs)
    return ds_out


def find_static_regions(
    data: pd.Series,
    diff_period: int,
    static_limit: float,
) -> pd.Series:
    """
    Algorithm that ensures values can stay the same within the outliers_mask
    """
    diff = data.diff().fillna(method="ffill").abs()  # forward filling all NaNs!
    # Indexing is significantly faster on numpy arrays that pandas series
    diff = np.array(diff)
    outliers_mask = np.zeros_like(diff, dtype=bool)
    for i in range(len(outliers_mask) - diff_period + 1):
        i_end = i + diff_period
        if max(diff[i:i_end]) < static_limit:
            outliers_mask[i:i_end] = True
    return pd.Series(index=data.index, data=outliers_mask)