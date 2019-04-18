#!/usr/bin/env python

"""
ROS service source code generation for OWL.

Converts ROS .srv files into OWL ontologies.
"""

import os
import sys

import genowl.generator
import genowl.genowl_main

if __name__ == "__main__":
    genowl.genowl_main.genmain(sys.argv, 'gensrv_owl.py', genowl.generator.SrvGenerator())
