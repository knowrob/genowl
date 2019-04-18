#!/usr/bin/env python

"""
ROS message source code generation for OWL

Converts ROS .msg files in a package into OWL ontologies.
"""

import os
import sys

import genowl.generator
import genowl.genowl_main

if __name__ == "__main__":
    genowl.genowl_main.genmain(sys.argv, 'genmsg_owl.py', genowl.generator.MsgGenerator())
