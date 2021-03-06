function result = test(varargin)
    %testWavesurfer  Run wavesurfer automated tests.
    %
    %   testWavesurfer() runs all wavesurfer automated tests.
    %
    %   testWavesurfer('nohow') runs only those test that do not require
    %   any hardware connection.
    %
    %   res = testWavesurfer() returns test results in the result
    %   structure, res, rather than displaying the results at the command
    %   line.

    % By default include the tests that don't require hardware.
    noHardwareTestSuite = matlab.unittest.TestSuite.fromPackage('ws.test.nohw');

    % Add the hardware tests if appropriate based on the input arguments.
    if any(strcmp('--nohw', varargin)) ,
        % Just the no-harware tests 
        testSuite = noHardwareTestSuite ;
    else
        withHardwareTestSuite = matlab.unittest.TestSuite.fromPackage('ws.test.hw');
        testSuite = horzcat(withHardwareTestSuite, noHardwareTestSuite) ;
    end

    % Deal with duplicate tests, which happens sometimes, for unknown
    % reasons
    test_names = {testSuite.Name} ;
    [unique_test_names, indices_of_unique_tests] = unique(test_names) ; %#ok<ASGLU>
    testSuiteWithAllUnique = testSuite(indices_of_unique_tests) ;
    if length(testSuiteWithAllUnique) ~= length(testSuite) ,
        warning('Sigh.  There seem to be duplicated tests...') ;
    end
    
    % Run the (unique) tests
    fprintf('About to perform %d tests...\n', length(testSuiteWithAllUnique)) ;
    result = testSuiteWithAllUnique.run() ;
end
