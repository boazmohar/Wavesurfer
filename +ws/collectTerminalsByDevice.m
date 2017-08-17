function [deviceNamePerDevice, terminalIDsPerDevice, channelIndicesPerDevice] = collectTerminalsByDevice(deviceNamePerChannel, terminalIDPerChannel)
    % This gets the device names and terminal IDs into the form that DABS wants
    % them in when calling task.createAIVoltageChan().  deviceNamePerChannel is
    % a 1 x nChannels cellstring, giving the device name for each channel.
    % terminalIDPerChannel is a 1 x nChannels double array, giving the terminal
    % ID for each channel.  On output, deviceNamePerDevice is a 1 x nDevices
    % cell string of all the unique device names in deviceNamePerChannel, with
    % no repeats. terminalIDsPerDevice is a 1 x nDevices cell array, each
    % element of which holds a double array containing the terminalIDs
    % associated with that device.
    
    [deviceNamePerDevice, ~, deviceIndexPerChannelAsCol] = unique(deviceNamePerChannel) ;
    deviceIndexPerChannel = deviceIndexPerChannelAsCol' ;

    % deviceIndex, here and below, is the position of a device within deviceNamePerDevice
    
    function terminalIDs = terminalIDsFromDeviceIndex(deviceIndex)
        terminalIDs = terminalIDPerChannel(deviceIndexPerChannel==deviceIndex) ;
    end    
    
    function channelIndices = channelIndicesFromDeviceIndex(deviceIndex)
        channelIndices = find(deviceIndexPerChannel==deviceIndex) ;
    end
    
    if nargout>=2 ,
        nDevices = length(deviceNamePerDevice) ;
        deviceIndexPerDevice = 1:nDevices ;
        
        terminalIDsPerDevice = ...
            arrayfun(@terminalIDsFromDeviceIndex, ...
                     deviceIndexPerDevice, ...
                     'UniformOutput', false) ;                                        
                 
        if nargout>=3 ,
            channelIndicesPerDevice = ...
                arrayfun(@channelIndicesFromDeviceIndex, ...
                         deviceIndexPerDevice, ...
                         'UniformOutput', false) ;
        end                                    
    end
end
