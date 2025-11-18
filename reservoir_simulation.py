import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# import and visualize data
outflow_data = pd.read_csv('4200 Modified Average Daily Streamflows.csv')
outflow_data.rename(columns={'Ice Harbor Daily Streamflows (unit:cfs)': 'Ice Harbor outflow (cfs)'}, inplace=True)
outflow_data.rename(columns={'Lower Monumental (unit:cfs)': 'Lower Monumental outflow (cfs)'}, inplace=True)
outflow_data.rename(columns={'Little Goose (unit:cfs)': 'Little Goose outflow (cfs)'}, inplace=True)
outflow_data.rename(columns={'Lower Granite (unit:cfs)': 'Lower Granite outflow (cfs)'}, inplace=True)
outflow_data['date'] = pd.to_datetime(outflow_data['date'])

#process precip data
precip_data = pd.read_csv('NOAAprecipitation_data_LEWISTON_AIRPORT_ID.csv')
precip_data = precip_data.drop(['STATION', 'NAME', 'LATITUDE', 'LONGITUDE', 'ELEVATION', 'SNWD', 'SNOW'], axis=1)
precip_data.rename(columns={'PRCP':'rainfall (in)', 'DATE':'datetime'}, inplace=True)
precip_data['datetime'] = pd.to_datetime(precip_data['datetime'], format='%Y-%m-%d')
end = precip_data['datetime'].max()
start = end - pd.DateOffset(years=10)
precip_10yr = precip_data[(precip_data['datetime'] >= start) & 
                          (precip_data['datetime'] <= end)]
#check and remove nans
# print(precip_10yr['rainfall (in)'].isna().any()) #returns True
precip_10yr.loc[:, 'rainfall (in)'] = precip_10yr['rainfall (in)'].fillna(0) #replaces nan with 0
# print(precip_10yr['rainfall (in)'].isna().any()) #returns False


# simulate reservoirs
x = 0
res_info = pd.DataFrame({'Names':['Ice Harbor','Lower Monumental','Little Goose','Lower Granite'],
                         'Reservoir surface area (m^2)':[9200*4047,6590*4047,10025*4047,8900*4047],
                         'Number of turbines':[6,6,6,6],
                         'Generation capacity (kW)':[603000,810000,903000,810000],
                         'Average tailwater elevation (m)':[x,x,x,x],
                         'Maximum pooling elevation (m)':[x,x,646.5,x],
                         'Watershed Area (m^2)':[103_352*4047 ,95_277*4047 ,83_074*4047 ,111_602*4047 ]
                         })
res_info = res_info.set_index('Names')
#test prints
# print(res_info)
# print(res_info.loc['Ice_Harbor','Watershed Area (m^2)'])

fish_passage = pd.DataFrame({'Names':['Ice Harbor','Lower Monumental','Little Goose','Lower Granite'], 'Fish Passage Rate (%)':[.965,.965,.9775,x]})
fish_passage = fish_passage.set_index('Names')

eta = 0.8 # efficiency of turbines, assumed value
rho = 998 # density of water, 1000 kg/m^3
g = 9.81 # gravitational acceleration, 9.81 m/s^2

#fish passage function
def simulate_fish_passage(dam_name, keep):
    #df is dataframe containing Dam Name and inflow outflow data?
    if keep == 1:
        fish_passage.loc[dam_name,'Fish Passage Rate (%)'] = 1 #check if this is wrong
    return None

# generate inflow from previous reservoir outflow/gage data, and added runoff data

#hard coded S and Ia values based of land use and CN (see exceo sheet)
# S = 0.0484 #meter
# I = 0.00968 #meter
S = 1.904761905 #inches
I = 0.380952381 #inches

def calc_runoff(dam_name):
    #takes in precip data as P and dam name dataframe as df
    #returns runoff volume over 10 year period
    Area = res_info.loc[dam_name,'Watershed Area (m^2)']
    P = precip_10yr['rainfall (in)']
    Q = np.where(P <= I, 0, (P-I)**2 / (P - I + S))
    # print(Q[1005])
    Q = Q*0.0254 #convert to meters
    Q_v = Q * Area 
    return np.sum(Q_v)

def simulate_inflow(data):
    #will take streamflow data and add runoff for Lower Granite Dam summed over 10 years

    return data #this part doesnt work yet + np.sum(calc_runoff('Lower Granite'))

# simulate reservoir
def simulate_reservoir(df, initial_storage, keep, resID):
    # df is a dataframe containing reservoir data. Has columns 'inflow (cfs)'
    #       and 'outflow (cfs)'. Timestep is in days.
    # keep is a boolean. Keep = 0, remove = 1
    # resID is the string name of the reservoir
    # this function will directly modify a DataFrame!
    info = res_info[res_info['Names'] == resID].iloc[0]
    df['storage (cf)'] = 0
    max_storage = info['Maximum pooling elevation (m)']*info['Reservoir surface area (m^2)']
    df.loc[0,'storage (cf)'] = initial_storage
    if keep == 0:
        df['storage (cf)'] = df['storage (cf)'].cumsum() + (df['inflow (cfs)'] - df['outflow (cfs)'])*86400
        df['storage (m^3)'] = np.minimum(df['storage (cf)']/35.315,max_storage)
        df['elevation head (m)'] = df['storage (m^3)']/info['Reservoir surface area (m^2)']
        df['power produced (kWh)'] = np.minimum(eta*rho*g*df['elevation head (m)']*df['storage (cf)']*info['Number of turbines'], info['Generation capacity (kW)'])
    else:
        df['storage (cf)'] = 0
        df['elevation head (m)'] = 0
        df['power produced (kWh)'] = 0
        df['outflow (cfs)'] = df['inflow (cfs)']

    return None

# simulate the whole system
def simulate_system(df):
    # - df is dataframe with Ice Harbor, Lower Monumental, Little Goose, and Lower Granite
    return None

# simulate Little Goose reservoir
little_goose = pd.DataFrame(outflow_data['Little Goose outflow (cfs)'])
little_goose['inflow (cfs)'] = simulate_inflow(little_goose['Little Goose outflow (cfs)']) #this will change when we figure out the inflow data
little_goose.rename(columns={'Little Goose outflow (cfs)':'outflow (cfs)'}, inplace=True)
# print(little_goose)

# simulate_reservoir(little_goose,100000,0,'Little Goose')


#test calc_runoff function
print(calc_runoff('Ice Harbor'))
print(calc_runoff('Lower Monumental'))

#test fish passage
print(fish_passage)
simulate_fish_passage('Ice Harbor', 1)
print(fish_passage)