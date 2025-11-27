import pandas as pd
import numpy as np
from datetime import datetime

# CONSTANTS: to calculate hydropower
eta = 0.8 # efficiency of turbines, assumed value
rho = 998 # density of water, 1000 kg/m^3
g = 9.81 # gravitational acceleration, 9.81 m/s^2

class Reservoir:

    def __init__(self, SA, num_turb, capacity, tail_elev, pool_elev, bottom_elev, fish_pass, area, pc, spillway_cap, date_built):
        self.SA = SA # reservoir surface area (sq m)
        self.num_turb = num_turb # number of turbines at dam
        self.capacity = capacity # generation capacity (kW)
        self.tail_elev = tail_elev*0.3046 # tailwater elevation (ft -> m)
        self.pool_elev = pool_elev*0.3046 # reservoir maximum pooling elevation (ft -> m)
        self.bottom_elev = bottom_elev*0.3046 # reservoir bottom elevation (ft -> m)
        self.fish_pass = fish_pass # fish passage rate
        self.area = area # watershed area (sq m)
        self.pc = pc # powerhouse capacity (cfs)
        self.spillway_cap= spillway_cap # spillway capacity (cfs)
        self.date_built=date_built #datetime for when dam construction was completed
        self.max_storage = self.SA * (self.pool_elev - self.bottom_elev) #m^3
    
    def simulate_fish_passage(self, keep):
        if keep == 0: # remove dam
            return 1
        return self.fish_pass

    def simulate_storage(self, keep, dstorage, initial_storage):
        '''Takes in storage height and out outflow and calculates dstorage?'''
        max_storage = self.max_storage #m^3
        storage = np.zeros(len(dstorage))
        if keep == 0: # no dam
            return storage
        
        else: #yes dam
            storage[0] = initial_storage
            for i in range(1,len(storage)):
                #just realized if we clip storage like this, then our stored dstorage (used to calculate other things) is wrong
                storage[i] = max(min(storage[i-1] + dstorage[i]*86400*0.0283, max_storage), 0) #units are m^3

                #rewrote is with loops, which I know is less efficient, but I hope that by overwriting and returning, we can fix possible propogating errors
                # storage[i] = storage[i-1] + dstorage[i]*86400*0.0283 #units are m^3
                # if storage[i] < 0:
                #         storage[i] = 0
                #         dstorage[i] = storage[i] - storage[i-1]
                # elif storage[i] > self.max_storage:
                #      storage[i] = self.max_storage
                #      dstorage[i] = storage[i] - storage[i-1]

        return storage #m^3
    
    
    # def simulate_storage_outflow(self, keep, datetime, dstorage, outflow, tributary, MEF):
    #     max_storage = self.max_storage #m^3
        
    #     storage = pd.DataFrame({'date': datetime, 'storage (m^3)': np.zeros(len(dstorage))})
    #     if keep == 0: # no dam
    #         return storage
        
    #     elif keep == 1: #yes dam
    #         if storage['date'] >= self.date_built:
    #             storage['storage (m^3)'] = max(min(storage['storage (m^3'] + dstorage[i]*86400*0.0283, max_storage), 0) #units are m^3
    #             outflow['flow'] = outflow + (tributary-dstorage)*86400*.0283 #m^3/day
    #         if outflow['flow'] < MEF:
    #             for i in range(1,len(storage)):
    #                 storage[i] = max(min(storage[i-1] + dstorage[i]*86400*0.0283, max_storage), 0) #units are m^3

    #     return outflow, storage #m^3/d, m^3

    def simulate_outflow(self, prev_out, tributary, dstorage):
        return prev_out + (tributary-dstorage)*86400*.0283 #m^3/day
    
    def simulate_storage_outflow_new(self, keep, prev_out, tributary, storage, dstorage, initial_storage):
        ''' loops over storage and calculates outflow instead of using dstorage 
        prev_out = previous dam's outflow array
        tributary = tributary inflow array
        storage = computed storage array

        returns completed outflow array
        '''
        max_storage = self.max_storage #m^3
        storage = np.zeros(len(dstorage))

        out = prev_out.copy()
        if keep == 0: # no dam
            return storage, out
        
        else: #yes dam
            storage[0] = initial_storage
            for i in range(1,len(storage)):
                storage[i] = max(min(storage[i-1] + dstorage[i-1]*86400*0.0283, max_storage), 0) #units are m^3
                out[i] = prev_out[i-1] + tributary[i-1]*86400*.0283 + (storage[i-1]-storage[i])
                if out[i] < 0:
                    out[i] = 0
                    ds = out[i] - out[i-1]
                    storage[i] = storage[i-1] + ds*86400


        return storage, out #m^3, m^3/d

    def calculate_dstorage(inflow, outflow):
        return inflow - outflow
    
#MOST RECENT ATTEMPT HERE

    def sim_dstor(self, water_heights):
        stor = water_heights *self.SA #m^3
        dstor = stor - stor.shift()
        return stor, dstor

    def inflows(self,prev_dam_out, trib):
        return prev_dam_out + trib*86400*.0283
    
    def outflow(self, inflow, dstorage):
        out = inflow - dstorage
        return out
#HERE 

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
    


    ##ALSO HERE
    def simulation(self, keep, datetime, prev_out, tributary, water_heights):
        # make calculations
        fish_passage = self.simulate_fish_passage(keep)
        inflow = self.inflows(prev_out,tributary)
        storage, dstorage = self.sim_dstor(water_heights)
        outflow = self.outflow(inflow, dstorage) #inputs m^3/day,cfs; outputs m^3/day
        head = self.simulate_head(storage) #inputs m^3, outputs m
        hydro = self.simulate_hydropower(head, outflow, keep) #inputs m and m^3/day, outputs kWh
        avg_hydro = self.calc_avg_annual_hydro(datetime, hydro) #inputs kWh, outputs kWh/year
        
        return outflow, avg_hydro, fish_passage

    ######
    
    def simulate(self, keep, initial_storage, datetime, prev_out, tributary, dstorage):
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
        outflow = self.simulate_outflow(prev_out, tributary, dstorage) #inputs m^3/day,cfs; outputs m^3/day
        storage = self.simulate_storage(keep, dstorage, initial_storage) #inputs cfs, outputs m^3
        head = self.simulate_head(storage) #inputs m^3, outputs m
        hydro = self.simulate_hydropower(head, outflow, keep) #inputs m and m^3/day, outputs kWh
        avg_hydro = self.calc_avg_annual_hydro(datetime, hydro) #inputs kWh, outputs kWh/year
        
        return outflow, avg_hydro, fish_passage
    

    #made another version in an attempt to make sure dstorage is consistent
    def simulate_opt(self, keep, initial_storage, datetime, prev_out, tributary, dstorage, MEF):
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
        storage = self.simulate_storage(keep, dstorage, initial_storage) #inputs cfs, outputs m^3
        # storagein = storage
        #simulate_outflow_new(self, prev_out, tributary, storage)
        outflow = self.simulate_outflow_new(prev_out, tributary, storage) #inputs m^3/day,cfs; outputs m^3/day
        # for i, out in enumerate(outflow):
        #     if out < MEF:
        #         outflow[i] = MEF
        #         dstorage[i] = outflow[i] - tributary[i]*86400*.0283 - prev_out[i]
        # if dstorageupdated != dstorage:
        #     print('dstorage changed')
        #     d, storagein = self.simulate_storage(keep, dstorageupdated, initial_storage) #inputs cfs, outputs m^3
        head = self.simulate_head(storage) #inputs m^3, outputs m
        hydro = self.simulate_hydropower(head, outflow, keep) #inputs m and m^3/day, outputs kWh
        avg_hydro = self.calc_avg_annual_hydro(datetime, hydro) #inputs kWh, outputs kWh/year
        
        return outflow, avg_hydro, fish_passage