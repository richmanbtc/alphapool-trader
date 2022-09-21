#!/bin/bash

coverage run -m unittest discover -v
exit_code=$?
coverage html -d /tmp/alphapool-trader/htmlcov

exit $exit_code
