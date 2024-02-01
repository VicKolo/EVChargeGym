"""
This file is used to assess the battery drgradation model.

"""

from EVsSimulator.EVsimulator.models.ev import EV
import sys
import os
sys.path.append(os.path.realpath('../'))


def battery_degradation():


    timescale = 60 # 1 hour
    
    # initialzing an EV

    ev = EV(id=0,
            location=0,
            battery_capacity_at_arrival=10,
            battery_capacity=50,
            time_of_arrival=0,
            time_of_departure=100,            
            transition_soc=0.9999,
            timescale=timescale,
            simulation_length = 1000,)


if __name__ == "__main__":
    battery_degradation()
