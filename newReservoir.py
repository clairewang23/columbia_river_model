import pandas as pd
import numpy as np

# CONSTANTS: to calculate hydropower
eta = 0.8 # efficiency of turbines, assumed value
rho = 998 # density of water, 1000 kg/m^3
g = 9.81 # gravitational acceleration, 9.81 m/s^2

class Reservoir:

    def __init__(self, SA, num_turb, capacity, tail_elev, pool_elev, bottom_elev, fish_pass, area, pc):
        self.SA = SA # reservoir surface area (sq m)
        self.num_turb = num_turb # number of turbines at dam
        self.capacity = capacity # generation capacity (kW)
        self.tail_elev = tail_elev*0.3046 # tailwater elevation (ft -> m)
        self.pool_elev = pool_elev*0.3046 # reservoir maximum pooling elevation (ft -> m)
        self.bottom_elev = bottom_elev*0.3046 # reservoir bottom elevation (ft -> m)
        self.fish_pass = fish_pass # fish passage rate
        self.area = area # watershed area (sq m)
        self.pc = pc # powerhouse capacity (cfs)
        self.max_storage = SA * (pool_elev - bottom_elev)
    
    def simulate_fish_passage(self, keep):
        if keep == 0: # remove dam
            return 1
        return self.fish_pass
    
    def simulate_storage(self, initial_storage, keep, dstorage, outflow):
        max_storage = self.max_storage
        storage = np.zeros(len(outflow))

        if keep == 0: # no dam
            return storage
        
        # else: yes dam
        storage[0] = initial_storage
        for i in range(1,len(storage)):
            storage[i] = max(min(storage[i-1] + dstorage[i]*86400*0.0283, max_storage), 0)
        
        return storage
    
    def simulate_head(self, storage):
        water_height = storage/self.SA + self.bottom_elev
        head = water_height - self.tail_elev
        return head*0.3048
    
    def simulate_hydropower(self, head, flow, keep):
        inflow = np.minimum(flow, self.pc)
        P = rho * g * head * eta * self.num_turb * inflow*0.0283

        if keep == 0: # no dam
            P = 0
        # else: yes dam
        P = np.maximum(P, 0) # non-negativity constraint
        P = np.minimum((P/1000), self.capacity) # maximum power output is less than rated capacity of turbine
        energy = (P/1000) * 24 # Watts to kW multiplied by hours in a day to get kWh=
        return energy

    def calc_avg_annual_hydro(self, date, hydro):
        data = pd.DataFrame({'date':date, 'hydro':hydro})
        avg_annual_hydro = data.groupby(data['date'].dt.year)['hydro'].mean()
        return avg_annual_hydro
    
    def simulate(self, keep, initial_storage, datetime, outflow, dstorage):
        '''
        Inputs:
        - keep: if dam is kept, has value of 1. If dam is removed, has value of 0. 
        - datetime: array of datetime values for each datapoint
        - outflow: array of reservoir outflow values (cfs)
        - dstorage: array of reservoir change in storage values (cfs)
        Return Dataframe containing reservoir simulation data.
        Dataframe includes columns: datetime, outflow, dstorage, storage, hydropower
        '''
        # simulated_reservoir = pd.DataFrame({'Datetime':datetime,'Outflow (cfs)':outflow,'Dstorage (cfs)':dstorage})

        # make calculations
        fish_passage = self.simulate_fish_passage(keep)
        storage = self.simulate_storage(initial_storage, keep, dstorage, outflow)
        head = self.simulate_head(storage)
        hydro = self.simulate_hydropower(head, outflow, keep)
        avg_hydro = self.calc_avg_annual_hydro(datetime, hydro)
        
        # put results in dataframe
        # simulated_reservoir['storage'] = storage
        # simulated_reservoir['head'] = head
        # simulated_reservoir['hydro'] = hydro
        return avg_hydro, fish_passage