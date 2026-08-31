import multiprocessing
import os
import sys
multiprocessing.freeze_support()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gui.app import run
if __name__ == '__main__':
    run()
