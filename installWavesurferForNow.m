function installWavesurferForNow()
    % Allow user to invoke Wavesurfer from the Matlab command line, for
    % this Matlab session only.  Modifies the user's Matlab path, but does
    % not safe the modified path.

    wavesurferPath = which('wavesurfer');

    % This really shouldn't happen given that this function is distributed in the
    % same directory as wavesurfer.m.
    if isempty(wavesurferPath) ,
        error('wavesurfer:configureFailure', 'Wavesurfer does not appear to be installed correctly.  wavesurfer.m is missing.\n');
    end

    wavesurferParentFolder=fileparts(wavesurferPath);
    addpath(wavesurferParentFolder);
    addpath(fullfile(wavesurferParentFolder,'wavesurfer_guis'));
    addpath(fullfile(wavesurferParentFolder,'matlab-zmq','lib'));
end
