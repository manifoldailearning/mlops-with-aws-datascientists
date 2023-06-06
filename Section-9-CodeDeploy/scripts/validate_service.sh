#!/bin/bash

# verify we can access our webpage successfully
curl -v --silent localhost:80 2>&1 | grep AWS