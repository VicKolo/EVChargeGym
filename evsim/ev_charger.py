'''
===================================
Author: Stavros Orfanoudakis 2023
===================================
'''

import numpy as np
from .ev import EV
import math

class EV_Charger:
    '''
    This file contains the EV_Charger class, which is used to represent the EV chargers in the environment.

    Attributes:
        - id: unique identifier of the EV charger
        - connected_bus: the bus to which the EV charger is connected
        - connected_transformer: the transformer(s) to which the EV charger is connected
        - geo_location: the geographical location of the EV charger
        - max_charge_power: the maximum total power that the EV charger can provide to all EVs connected to it per hour
        - max_discharge_power: the maximum total power that the EV charger can receive from all EVs connected to it per hour
        - n_ports: the number of ports of the EV charger
        - charger_type: the type of the EV charger (typ1, type2, or DC)
        - bi_directional: whether the EV charger can provide power to the grid or not
        - timescale: the timescale of the simulation (useful for determining the charging speed)
        - verbose: whether to print information about the EV charger or not

    Status variables:
        - current_power_output: the current total power output of the EV charger (positive for draining energy from the grid, negative for providing energy to the grid)
        - evs_connected: the list of EVs connected to the EV charger
        - n_ev_connected: the current number of EVs connected to the EV charger
        - current_step: the current simulation timestep

    Statistics variables:
        - total_energy_charged: the total energy charged by the EV charger  
        - total_energy_discharged: the total energy discharged by the EV charger
        - total_profits: the total profit of the EV charger
        - total_evs_served: the total number of EVs served by the EV charger
        - total_user_satisfaction: the total user satisfaction of the EV charger

    Methods:
        - step: updates the EV charger status according to the actions taken by the EVs
        - reset: resets the EV charger status to the initial state              
'''

    def __init__(self,
                 id,
                 connected_bus,
                 connected_transformer,
                 geo_location=None,
                 min_charge_current=8,  # Amperes
                 max_charge_current=32,  # Amperes                 
                 min_discharge_current= -8,  # Amperes
                 max_discharge_current= -32,  # Amperes
                 voltage=230,  # Volts
                 n_ports=2,
                 charger_type="AC",  # AC or DC
                 bi_directional=True,
                 timescale=5,
                 verbose=False):

        self.id = id

        # EV Charger location and grid characteristics
        self.connected_bus = connected_bus
        self.connected_transformer = connected_transformer
        self.geo_location = geo_location

        # EV Charger technical characteristics                
        self.n_ports = n_ports
        self.charger_type = charger_type
        self.bi_directional = bi_directional
        self.timescale = timescale

        self.min_charge_current = min_charge_current
        self.max_charge_current = max_charge_current
        self.min_discharge_current = min_discharge_current
        self.max_discharge_current = max_discharge_current

        self.voltage = voltage

        # EV Charger status
        self.current_power_output = 0
        self.evs_connected = [None] * n_ports
        self.n_evs_connected = 0
        self.current_step = 0
        self.current_charge_price = 0
        self.current_discharge_price = 0
        self.current_total_amps = 0

        # EV Charger Statistics
        self.total_energy_charged = 0
        self.total_energy_discharged = 0
        self.total_profits = 0
        self.total_evs_served = 0
        self.total_user_satisfaction = 0

        self.verbose = verbose

    def step(self, actions, charge_price, discharge_price):
        '''
        Updates the EV charger status according to the actions taken by the EVs
        Inputs:
            - actions: a list of actions taken by the EVs connected to the EV charger in the format of (power) *n_ports positive for charging negative for discharging, default is to zer if no ev is connected        
            - charge_price: the price of charging per kWh in the current timestep
            - discharge_price: the price of discharging per kWh in the current timestep

        Outputs:
            - profit: the total profit + costs of charging and discharging in the current timestep
            - user_satisfaction: a list of user satisfaction values for each EV connected to the EV charger in the current timestep
        '''
        profit = 0
        user_satisfaction = []
        self.current_power_output = 0
        self.current_total_amps = 0
        self.current_charge_price = charge_price
        self.current_discharge_price = discharge_price

        assert (len(actions) == self.n_ports)
        # if no EV is connected, set action to 0
        invalid_action_punishment = 0
        for i in range(len(actions)):
            if self.evs_connected[i] is None:
                actions[i] = 0
                invalid_action_punishment += 1

        # normalize actions to sum to 1 for charging surplass or -1 for discharging surplass
        if sum(actions) > 1:
            normalized_actions = [action / sum(actions) for action in actions]
        elif sum(actions) < -1:
            normalized_actions = [- action /
                                  sum(actions) for action in actions]
        else:
            normalized_actions = actions

        if self.verbose:
            print(f'CS {self.id} normalized actions: {normalized_actions}')

        # Update EVs connected to the EV charger and get profits/costs
        for i, action in enumerate(normalized_actions):
            action = round(action, 5)
            assert action >= -1 and action <= 1

            if action == 0 and self.evs_connected[i] is not None:
                self.evs_connected[i].step(0)

            elif action > 0:
                amps = action * self.max_charge_current
                if amps < self.min_charge_current:
                    amps = 0
                    
                actual_power, actual_amps = self.evs_connected[i].step(
                    amps,
                    self.voltage,
                    type=self.charger_type)
                profit += abs(actual_power) * charge_price
                self.total_energy_charged += abs(actual_power)
                self.current_power_output += actual_power
                self.current_total_amps += actual_amps

            elif action < 0:
                if not self.bi_directional:
                    actual_power, actual_power = 0, 0
                else:
                    amps = action * abs(self.max_charge_current)
                    if amps > self.min_discharge_current:
                        amps = self.min_discharge_current                    
                    
                    actual_power, actual_amps = self.evs_connected[i].step(
                        amps,
                        self.voltage,
                        type=self.charger_type)
                profit += abs(actual_power) * discharge_price
                self.total_energy_discharged += abs(actual_power)
                self.current_power_output += actual_power
                self.current_total_amps += actual_amps
            
            if self.current_total_amps - 0.0001 > self.max_charge_current:
                raise Exception(f'sum of amps {self.current_total_amps} is higher than max charge current {self.max_charge_current}')

            if self.verbose and self.evs_connected[i] is not None:
                print(f'Actual power: {actual_power} kW' +
                      f' | Actual amps: {actual_amps} A' +
                      f' | Action: {action}'
                      )

        self.total_profits += profit

        # Check if EVs are departing
        for i, ev in enumerate(self.evs_connected):
            if ev is not None:
                # print(f'EV {ev.id} check departure step {self.current_step}' +\
                #       f' earlier time of departure {ev.earlier_time_of_departure}' +\
                #       f', Is departing: {ev.is_departing(self.current_step)}')
                if ev.is_departing(self.current_step) is not None:
                    self.evs_connected[i] = None
                    self.n_evs_connected -= 1
                    self.total_evs_served += 1
                    ev_user_satisfaction = ev.get_user_satisfaction()
                    self.total_user_satisfaction += ev_user_satisfaction
                    user_satisfaction.append(ev_user_satisfaction)
                    if self.verbose:
                        print(f'- EV {ev.id} is departing from CS {self.id}' +
                              f' port {i}'
                              f' with user satisfaction {ev_user_satisfaction}' +
                              f' (SoC: {ev.get_soc()*100: 6.1f}%)')

        self.current_step += 1

        return profit, user_satisfaction, invalid_action_punishment

    def get_state(self):
        '''
        Returns the state of the EV charger
        '''
        state = [self.current_charge_price,
                 self.current_discharge_price,
                 #  self.max_charge_power/1000, # Transform to MW for better scaling
                 #  self.max_discharge_power/1000, #MW
                 #  self.n_ports,
                 #  self.n_evs_connected
                 ]

        for EV in self.evs_connected:
            if EV is not None:
                state.append(EV.get_state(self.current_step))
            else:
                state.append(np.zeros(2))

        return np.hstack(state)

    def __str__(self) -> str:

        if self.total_evs_served == 0:
            user_satisfaction_str = ' Avg. Sat.:  - '
        else:
            user_satisfaction_str = f' Avg. Sat.: {self.get_avg_user_satisfaction()*100: 3.1f}%'

        # f' ({self.current_step*self.timescale: 3d} mins)' + \
        return f'CS{self.id:3d}: ' + \
            f' Served {self.total_evs_served:4d} EVs' + \
            user_satisfaction_str + \
            f' in {self.current_step: 4d} steps' + \
            f' |{self.total_profits: 7.1f} € |' + \
            f' +{self.total_energy_charged: 5.1f} /' + \
            f' -{self.total_energy_discharged: 5.1f} kW'

    def get_avg_user_satisfaction(self):
        if self.total_evs_served == 0:
            return 0
        else:
            return self.total_user_satisfaction / self.total_evs_served

    def spawn_ev(self, ev):
        '''Adds an EV to the list of EVs connected to the EV charger
        Inputs:
            - ev: the EV to be added to the list of EVs connected to the EV charger
        '''
        assert (self.n_evs_connected < self.n_ports)

        index = self.evs_connected.index(None)
        ev.id = index
        self.evs_connected[index] = ev
        self.n_evs_connected += 1

        if self.verbose:
            print(f'+ EV connected to Charger {self.id} at port {index}' +
                  f' leaving at {ev.earlier_time_of_departure}' +
                  f' SoC {ev.get_soc()*100:.1f}%')

        return index

    def reset(self):
        '''Resets the EV charger status to the initial state'''

        # EV Charger status
        self.current_power_output = 0
        self.current_total_amps = 0
        self.evs_connected = [None] * self.n_ports
        self.n_evs_connected = 0
        self.current_step = 0

        # EV Charger Statistics
        self.total_energy_charged = 0
        self.total_energy_discharged = 0
        self.total_profits = 0
        self.total_evs_served = 0
        self.total_user_satisfaction = 0
