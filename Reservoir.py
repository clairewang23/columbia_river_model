import pandas as pd
import numpy as np

# CONSTANTS: hard coded S and Ia values based of land use and CN (see Excel sheet)
S = 1.904761905 #inches
I = 0.380952381 #inches

# CONSTANTS: to calculate hydropower
eta = 0.8 # efficiency of turbines, assumed value
rho = 998 # density of water, 1000 kg/m^3
g = 9.81 # gravitational acceleration, 9.81 m/s^2

class Reservoir:

    def __init__(self, SA, num_turb, capacity, tail_elev, pool_elev, bottom_elev, fish_pass, area):
        self.SA = SA # reservoir surface area (sq m)
        self.num_turb = num_turb # number of turbines at dam
        self.capacity = capacity # generation capacity (kW)
        self.tail_elev = tail_elev*0.3046 # tailwater elevation (ft -> m)
        self.pool_elev = pool_elev*0.3046 # reservoir maximum pooling elevation (ft -> m)
        self.bottom_elev = bottom_elev*0.3046 # reservoir bottom elevation (ft -> m)
        self.fish_pass = fish_pass # fish passage rate
        self.area = area # watershed area (sq m)
        self.max_storage = SA * (pool_elev - bottom_elev)
    
    def simulate_fish_passage(self, keep):
        if keep == 1: # remove dam
            return 1
        return self.fish_pass
    
    def calc_runoff(self, precip_data):
        Area = self.area
        P = precip_data
        Q = np.where(P <= I, 0, (P-I)**2 / (P - I + S))
        Q = Q*0.0254 #convert to meters
        Q_v = Q * Area 
        return Q_v
    
    def simulate_inflow(self, precip_data, inflow_data):
        runoff = self.calc_runoff(precip_data) # gives volume per day (m^3/d)
        upstream_flow = inflow_data*86400*0.0283 # gives volume per day (m^3/d)
        return runoff + upstream_flow
    
    def simulate_storage(self, initial_storage, keep, inflow, outflow):
        max_storage = self.max_storage
        storage = np.zeros(len(inflow))

        if keep == 0: # no dam
            return storage
        
        # else: yes dam
        storage[0] = initial_storage
        for i in range(1,len(storage)):
            storage[i] = max(min(storage[i-1] + inflow[i] - outflow[i], max_storage), 0)
        
        return storage
    
    def simulate_head(self, storage):
        return None
    
    def simulate_hydropower(self, head, flow, keep):
        P = rho * g * head * eta * self.num_turb * flow

        if keep == 0: # no dam
            P = 0
        # else: yes dam
        P = min((P/1000), self.capacity) # maximum power output is less than rated capacity of turbine
        P = max(P, 0) # non-negativity constraint
        energy = (P/1000) * 24 # Watts to kW multiplied by hours in a day to get kWh=
        return energy
    
