"""
Conftest for predictive tests.
Adds the predictive package directory to sys.path so bare imports work.
"""
import sys
import os

# Add the predictive package directory to sys.path
predictive_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.abspath(predictive_dir))
