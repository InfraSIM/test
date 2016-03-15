# Running Integration Tests

## Setup

Make sure python2.x has been installed on you test director system.

Git clone this repository and then:

    cd install/
    sudo python PackageInstall.py

## Running the tests

    python puffer.py --stack <target_stack> -s <test_suite> [-c <case_number>[,<case_number>,...]]

## Parameters

Set target stack and load configuration:

    --stack <target_stack>

Select folder path of the test suites, separated by `,` based on `case\`:

    -s <test_suite>
    --suite <test_suite>

Select test case, digit test cases numbers to be executed, separated by `,`;
Test case script file should be in `case\` or its sub-folder:

    -c <case_number>[,<case_number>,...]
    --case <case_number>[,<case_number>,...]

Select file containing a list of test cases/suites:

    -l <case_list>
    --list <case_list>

To get more options, run:

    python puffer.py -h
