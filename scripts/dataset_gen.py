import pandas as pd
import numpy as np

# Sample data to be replicated
data = [
    {
        'GUID': '1', 'Density (kg/m³)': 2770, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': '3A51918F-AB60-4CE7-A771-A10C3266684A', 'eBKP-H': 'C03.01'
    },
    {
        'GUID': '2', 'Density (kg/m³)': 439, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': '75F8C2B2-0B4E-4243-93D6-9D8B721B4D12', 'eBKP-H': 'C03.02'
    },
    {
        'GUID': '3', 'Density (kg/m³)': 34.3, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': 'ACF64203-B038-4EAF-B297-53D8C48F8A42', 'eBKP-H': 'C04.01'
    },
    {
        'GUID': '4', 'Density (kg/m³)': 1400, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': '1300707C-F4F2-4FDC-AF3B-E31F5840F18E', 'eBKP-H': 'C04.04'
    },
    {
        'GUID': '5', 'Density (kg/m³)': 2300, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': 'E13EE05E-FD34-4FB5-A178-0FC4164A96F2', 'eBKP-H': 'C04.05'
    },
    {
        'GUID': '6', 'Density (kg/m³)': 605, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': 'BD66B05D-27E3-4ADF-85A2-E0ABBBA686A5', 'eBKP-H': 'C04.08'
    },
    {
        'GUID': '7', 'Density (kg/m³)': 7850, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': '4DC70979-B6CA-4DA5-A291-6F1A082EE475', 'eBKP-H': 'C04.01'
    },
    {
        'GUID': '8', 'Density (kg/m³)': 148, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': 'B9689582-8BDE-4FE1-849D-BBBED840E410', 'eBKP-H': 'C04.04'
    },
    {
        'GUID': '9', 'Density (kg/m³)': 7850, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': '38C1572A-3CE8-47C0-B24E-5E924A8AD97E', 'eBKP-H': 'C04.05'
    },
    {
        'GUID': '10', 'Density (kg/m³)': 1500, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': '9831C103-3AC5-439B-9BF1-3C1976328C98', 'eBKP-H': 'E02.05'
    },
    {
        'GUID': '11', 'Density (kg/m³)': 2300, 'Volume': 1, 'Length': 1, 'Area': 1, 'KBOB UUID-Nummer': 'E13EE05E-FD34-4FB5-A178-0FC4164A96F2', 'eBKP-H': 'F01.02'
    }

]

# Convert the sample data to a DataFrame
df_sample = pd.DataFrame(data)

# Desired number of rows in the large dataset
num_rows = 100000

# Calculate how many times we need to replicate the sample data
num_repeats = int(np.ceil(num_rows / len(df_sample)))

# Replicate the DataFrame
df_large = pd.concat([df_sample] * num_repeats, ignore_index=True)

# Trim the DataFrame to the desired number of rows
df_large = df_large.iloc[:num_rows]

# Set a random seed for reproducibility
np.random.seed(0)

# Define ranges for each column that needs to vary
density_min, density_max = 400, 3000      
volume_min, volume_max = 0.1, 100         
length_min, length_max = 0, 500           
area_min, area_max = 0, 1000              

# Generate random values within the specified ranges
df_large['Density (kg/m³)'] = np.random.uniform(density_min, density_max, size=num_rows)
df_large['Volume'] = np.random.uniform(volume_min, volume_max, size=num_rows)
df_large['Length'] = np.random.uniform(length_min, length_max, size=num_rows)
df_large['Area'] = np.random.uniform(area_min, area_max, size=num_rows)

# Optional: Round the values to make them more realistic
df_large['Density (kg/m³)'] = df_large['Density (kg/m³)'].round(2)
df_large['Volume'] = df_large['Volume'].round(4)
df_large['Length'] = df_large['Length'].round(2)
df_large['Area'] = df_large['Area'].round(2)

# Save the large dataset to a CSV file
df_large.to_csv('NHMzh-modules/data/input/large_dataset.csv', index=False)

print(f"Large dataset with {num_rows} rows has been generated and saved to 'large_dataset.csv'.")
