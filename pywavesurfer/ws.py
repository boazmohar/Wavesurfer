import os
import math
import numpy
import h5py


def loadDataFile(filename, format_string='double'):
    """ Loads Wavesurfer data file.

    :param filename: File to load (has to be with .h5 extension)
    :param format_string: optional: the return type of the data, defaults to double. Could be 'single', or 'raw'.
    :return: dictionary with a structure array with one element per sweep in the data file.
    """
    # Check that file exists
    if not os.path.isfile(filename):
        raise IOError("The file %s does not exist." % filename)

    # Check that file has proper extension
    (_, ext) = os.path.splitext(filename)
    if ext != ".h5":
        raise RuntimeError("File must be a WaveSurfer-generated HDF5 (.h5) file.")

    # Extract dataset at each group level, recursively.
    file = h5py.File(filename)
    data_file_as_dict = crawl_h5_group(file)  # an h5py File is also a Group

    # Correct the samples rates for files that were generated by versions
    # of WS which didn't coerce the sampling rate to an allowed rate.
    header = data_file_as_dict["header"]
    if "VersionString" in header:
        version_string = header["VersionString"]  # this is a scalar numpy array with a weird datatype
        version = float(version_string.tostring().decode('utf-8'))
    else:
        # If no VersionsString field, the file is from an old old version
        version = 0
    if version < 0.9125:  # version 0.912 has the problem, version 0.913 does not
        # Fix the acquisition sample rate, if needed
        nominal_acquisition_sample_rate = float(header["Acquisition"]["SampleRate"])
        nominal_n_timebase_ticks_per_sample = 100.0e6 / nominal_acquisition_sample_rate
        if nominal_n_timebase_ticks_per_sample != round(
                nominal_n_timebase_ticks_per_sample):  # should use the python round, not numpy round
            actual_acquisition_sample_rate = 100.0e6 / math.floor(
                nominal_n_timebase_ticks_per_sample)  # sic: the boards floor() for acq, but round() for stim
            header["Acquisition"]["SampleRate"] = numpy.array(actual_acquisition_sample_rate)
            data_file_as_dict["header"] = header
        # Fix the stimulation sample rate, if needed
        nominal_stimulation_sample_rate = float(header["Stimulation"]["SampleRate"])
        nominal_n_timebase_ticks_per_sample = 100.0e6 / nominal_stimulation_sample_rate
        if nominal_n_timebase_ticks_per_sample != round(nominal_n_timebase_ticks_per_sample):
            actual_stimulation_sample_rate = 100.0e6 / round(
                nominal_n_timebase_ticks_per_sample)  # sic: the boards floor() for acq, but round() for stim
            header["Stimulation"]["SampleRate"] = numpy.array(actual_stimulation_sample_rate)
            data_file_as_dict["header"] = header

    # If needed, use the analog scaling coefficients and scales to convert the
    # analog scans from counts to experimental units.
    if "NAIChannels" in header:
        n_a_i_channels = header["NAIChannels"]
    else:
        acq = header["Acquisition"]
        if "AnalogChannelScales" in acq:
            all_analog_channel_scales = acq["AnalogChannelScales"]
        else:
            # This is presumably a very old file, from before we supported digital inputs
            all_analog_channel_scales = acq["ChannelScales"]
        n_a_i_channels = all_analog_channel_scales.size  # element count
    if format_string.lower() != "raw" and n_a_i_channels > 0:
        try:
            if "AIChannelScales" in header:
                # Newer files have this field, and lack header.Acquisition.AnalogChannelScales
                all_analog_channel_scales = header["AIChannelScales"]
            else:
                # Fallback for older files
                all_analog_channel_scales = header["Acquisition"]["AnalogChannelScales"]
        except KeyError:
            raise KeyError("Unable to read channel scale information from file.")
        try:
            if "IsAIChannelActive" in header:
                # Newer files have this field, and lack header.Acquisition.AnalogChannelScales
                is_active = header["IsAIChannelActive"].astype(bool)
            else:
                # Fallback for older files
                is_active = header["Acquisition"]["IsAnalogChannelActive"].astype(bool)
        except KeyError:
            raise KeyError("Unable to read active/inactive channel information from file.")
        analog_channel_scales = all_analog_channel_scales[is_active]

        # read the scaling coefficients
        try:
            if "AIScalingCoefficients" in header:
                analog_scaling_coefficients = header["AIScalingCoefficients"]
            else:
                analog_scaling_coefficients = header["Acquisition"]["AnalogScalingCoefficients"]
        except KeyError:
            raise KeyError("Unable to read channel scaling coefficients from file.")

        does_user_want_single = (format_string.lower() == "single")
        for field_name in data_file_as_dict:
            # field_names = field_namess{i}
            if len(field_name) >= 5 and (field_name[0:5] == "sweep" or field_name[0:5] == "trial"):
                # We check for "trial" for backward-compatibility with
                # data files produced by older versions of WS.
                analog_data_as_counts = data_file_as_dict[field_name]["analogScans"]
                if does_user_want_single:
                    scaled_analog_data = scaled_single_analog_data_from_raw(analog_data_as_counts,
                                                                            analog_channel_scales,
                                                                            analog_scaling_coefficients)
                else:
                    scaled_analog_data = scaled_double_analog_data_from_raw(analog_data_as_counts,
                                                                            analog_channel_scales,
                                                                            analog_scaling_coefficients)
                data_file_as_dict[field_name]["analogScans"] = scaled_analog_data

    return data_file_as_dict


def crawl_h5_group(group):
    result = dict()

    item_names = list(group.keys())

    for item_name in item_names:
        item = group[item_name]
        if isinstance(item, h5py.Group):
            field_name = field_name_from_hdf_name(item_name)
            result[field_name] = crawl_h5_group(item)
        elif isinstance(item, h5py.Dataset):
            field_name = field_name_from_hdf_name(item_name)
            result[field_name] = item[()]
        else:
            pass

    return result


def field_name_from_hdf_name(hdf_name):
    # Convert the name of an HDF dataset/group to something that is a legal
    # Matlab struct field name.  We do this even in Python, just to be consistent.
    try:
        # the group/dataset name seems to be a number.  If it's an integer, we can deal, so check that.
        hdf_name_as_double = float(hdf_name)
        if hdf_name_as_double == round(hdf_name_as_double):
            # If get here, group name is an integer, so we prepend with an "n" to get a valid field name
            field_name = "n{:%s}".format(hdf_name)
        else:
            # Not an integer.  Give up.
            raise RuntimeError("Unable to convert group/dataset name {:%s} to a valid field name.".format(hdf_name))
    except ValueError:
        # This is actually a good thing, b/c it means the groupName is not
        # simply a number, which would be an illegal field name
        field_name = hdf_name

    return field_name


def scaled_double_analog_data_from_raw(data_as_ADC_counts, channel_scales, scaling_coefficients):
    # Function to convert raw ADC data as int16s to doubles, taking to the
    # per-channel scaling factors into account.
    #
    #   data_as_ADC_counts: n_channels x nScans int16 array
    #   channel_scales: double vector of length n_channels, each element having
    #                   (implicit) units of V/(native unit), where each
    #                   channel has its own native unit.
    #   scaling_coefficients: n_channels x nCoefficients  double array,
    #                        contains scaling coefficients for converting
    #                        ADC counts to volts at the ADC input.
    #
    #   scaled_data: nScans x n_channels double array containing the scaled
    #               data, each channel with it's own native unit.

    inverse_channel_scales = 1.0 / channel_scales  # if some channel scales are zero, this will lead to nans and/or infs
    n_channels = channel_scales.size
    scaled_data = numpy.empty(data_as_ADC_counts.shape)
    for i in range(0, n_channels):
        scaled_data[i, :] = inverse_channel_scales[i] * numpy.polyval(numpy.flipud(scaling_coefficients[i, :]),
                                                                      data_as_ADC_counts[i, :])
    return scaled_data


def scaled_single_analog_data_from_raw(dataAsADCCounts, channelScales, scalingCoefficients):
    scaledData = scaled_double_analog_data_from_raw(dataAsADCCounts, channelScales, scalingCoefficients)
    return scaledData.astype('single')