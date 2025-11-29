import pandas as pd
import numpy as np

# CONSTANTS: to calculate hydropower
eta = 0.8 # efficiency of turbines, assumed value
rho = 998 # density of water, 1000 kg/m^3
g = 9.81 # gravitational acceleration, 9.81 m/s^2

class Reservoir:

    def __init__(self, SA, num_turb, capacity, tail_elev, pool_elev, bottom_elev, fish_pass, area, pc, spillway_cap):
        self.SA = SA # reservoir surface area (sq m)
        self.num_turb = num_turb # number of turbines at dam
        self.capacity = capacity # generation capacity (kW)
        self.tail_elev = tail_elev*0.3046 # tailwater elevation (ft -> m)
        self.pool_elev = pool_elev*0.3046 # reservoir maximum pooling elevation (ft -> m)
        self.bottom_elev = bottom_elev*0.3046 # reservoir bottom elevation (ft -> m)
        self.fish_pass = fish_pass # fish passage rate
        self.area = area # watershed area (sq m)
        self.pc = pc # powerhouse capacity (cfs)
        self.spillway_cap = spillway_cap
        self.max_storage = self.SA * (self.pool_elev - self.bottom_elev) #m^3
    
    def simulate_fish_passage(self, keep):
        if keep == 0: # remove dam
            return 1
        return self.fish_pass
    
    def simulation_nat_lake(self, keep, param, h_in, n):
        """
        Simulate natural lake level, storage, and release trajectories.
        
        Parameters:
        - param (dict): Parameters for natural lake model with keys 'beta', 'alfa'
        - h_in (float): Initial lake level
        - n (array-like): Net inflows trajectory
        
        Returns:
        - tuple: (lake storage trajectory, lake level trajectory, release trajectory)
        """
        # Access parameters by dictionary keys
        S = self.SA      # Lake surface area [m^2]
        beta = param['beta'] # Storage-discharge parameter
        alfa = param['alfa'] # Storage-discharge parameter
        h0 = self.tail_elev    # Reference lake level [m]
        h_bottom = self.bottom_elev
        
        # Step of integration and simulation horizon
        H = len(n) - 1             # Simulation horizon [day]
        delta = 60 * 60 * 24       # Step of integration [s/day]

        if keep == 0:
            return np.zeros(len(n)), np.full(len(n), h0), n
        
        # Initialize variables for trajectories
        h = np.full(len(n), np.nan)  # Lake level [m]
        s = np.full(len(n), np.nan)  # Lake storage [m^3]
        r = np.full(len(n), np.nan)  # Lake release [m^3/s]

        # Set initial conditions
        h[0] = h_in
        s[0] = S * (h_in - h_bottom)  # Initial storage

        # Simulation loop
        for i in range(H):
            # Compute release
            r[i + 1] = min(beta * (h[i] - h0) ** alfa if h[i] > h0 else 0, s[i]/delta + n[i])
            # Update storage with balance equation
            s[i + 1] = s[i] + (n[i + 1] - r[i + 1]) * delta
            # Update lake level
            h[i + 1] = s[i + 1] / S + h_bottom
        
        return s, h, r

    def simulate_outflow(self, prev_out, tributary, dstorage):
        return prev_out + (tributary-dstorage)*86400*.0283 #m^3/day

    def simulate_head(self, storage):
        #storage given from sim_storage which outputs m^3, SA and elev in meters^2 and m
        water_height = storage/self.SA + self.bottom_elev # m
        head = water_height - self.tail_elev #m
        return head #m
    
    def simulate_hydropower(self, head, flow, keep):
        #flow from function: m^3/day
        #pc given in cfs
        inflow = np.minimum(flow, self.pc * 86400*.0283) #m^3/day
        if keep == 0: # no dam
            P = 0
        elif keep == 1: #yes dam
            #rho: kg/m^3
            #g: m/s^2
            #head: meters
            #inflow: CALCULATED FROM FUNCTION m^3/day (convert to m^3/s)
            #(kg*m*m*m^3)/(m^3*s^2*s) = (kg*m^2)/(s^3)
            P = rho * g * head * eta * inflow/86400 #Watts
            P = np.maximum(P, 0) # non-negativity constraint
            P = np.minimum(P/1000, self.capacity) # maximum power output is less than rated capacity of turbine, (converted to kW)
        energy = P * 24 # kW multiplied by hours in a day to get kWh

        return energy

    def calc_avg_annual_hydro(self, date, hydro):
        data = pd.DataFrame({'date':date, 'hydro':hydro})
        annual_hydro = data.groupby(data['date'].dt.year)['hydro'].sum()
        avg_annual_hydro = annual_hydro.mean()
        return avg_annual_hydro
    
    def simulate(self, keep, initial_storage, param, datetime, prev_out, tributary):
        '''
        Inputs:
        - keep: if dam is kept, has value of 1. If dam is removed, has value of 0. 
        - datetime: array of datetime values for each datapoint
        - outflow: array of reservoir outflow values (cfs)
        - dstorage: array of reservoir change in storage values (cfs)
        Return Dataframe containing reservoir simulation data.
        Dataframe includes columns: datetime, outflow, dstorage, storage, hydropower
        '''

        # make calculations
        fish_passage = self.simulate_fish_passage(keep)
        #outflow = self.simulate_outflow(prev_out, tributary, dstorage) #inputs m^3/day,cfs; outputs m^3/day

        storage, height, outflow = self.simulate_nat_lake(keep, param, initial_storage, prev_out + tributary)
        #head = self.simulate_head(storage) #inputs m^3, outputs m
        #hydro = self.simulate_hydropower(head, outflow, keep) #inputs m and m^3/day, outputs kWh
        #avg_hydro = self.calc_avg_annual_hydro(datetime, hydro) #inputs kWh, outputs kWh/year
        
        return None #outflow, avg_hydro, fish_passage