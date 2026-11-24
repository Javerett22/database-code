print("script started")
import pandas as pd
import sqlite3
from sqlalchemy import create_engine
import re
SCREENS = {1: 'crystal screen', 2: 'index', 3: 'peg ion', 4: 'salt rx', 5: 'wizard screen'}
def clean_condition_string(raw_string):
    if not raw_string:
        return ""
    # Strip out 'Average Ref. Index' followed by its float value (e.g., "Average Ref. Index 1.37105")
    # This regex handles variations with or without the period after 'Ref'
    cleaned = re.sub(r'Average\s+Ref\.?\s+Index\s+[\d.]+', '', raw_string, flags=re.IGNORECASE)
    # Clean up any leftover double spaces resulting from the removal
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned
def get_proper_well(pH_dict):
    updated_dict = {}
    
    for key, val in pH_dict.items():
        parts = key.split()
        
        # Check if it's a crystal screen and the last part is a number (1-96)
        if 'crystal screen' in key.lower() and parts and parts[-1].isdigit():
            num = int(parts[-1])
            if 1 <= num <= 96:
                row_letter = chr(65 + (num - 1) // 12)  # 0->A, 1->B, etc.
                col_number = ((num - 1) % 12) + 1       # 1 through 12
                well = f"{row_letter}{col_number}"
                
                # Create the new key with the well coordinate
                new_key = f"crystal screen {well}"
                updated_dict[new_key] = val
                
                # Optional: also add an 'xtal' alias if your database needs it
                updated_dict[f"xtal {well}"] = val
                continue
                
        # Keep all other keys (index, peg ion, etc.) unchanged
        updated_dict[key] = val
        
        
    return updated_dict

def get_matching_pH(raw_screen_string, pH_map):
    if not raw_screen_string:
        return None
        
    cleaned = raw_screen_string.lower().strip()
    
    # 1. Normalize screen name variants (handle hyphens and common abbreviations)
    cleaned = cleaned.replace("salt-rx", "salt rx").replace("peg-ion", "peg ion")
    cleaned = cleaned.replace("btmf", "bis-tris") # Adjust if your map calls it something else
    
    # 2. Extract the well coordinate (e.g., A1, E9, H12) near the beginning/middle
    # This regex looks for a letter A-H (or A-L) followed by 1-2 digits, ignoring anything after a dash/space/comma/underscore if it's an additive note
    well_match = re.search(r'\b([a-l]\d{1,2})\b', cleaned)
    
    if not well_match:
        return None
        
    well = well_match.group(1).upper()
    
    # 3. Identify which screen family it belongs to
    screen_prefix = None
    if "index" in cleaned:
        screen_prefix = "index"
    elif "peg ion" in cleaned:
        screen_prefix = "peg ion"
    elif "salt rx" in cleaned:
        screen_prefix = "salt rx"
    elif "wizard" in cleaned:
        screen_prefix = "wizard screen"
    elif "bis-tris" in cleaned or "btmf" in cleaned:
        screen_prefix = "bis-tris" # or whatever your map uses
    else:
        screen_prefix = "crystal screen" # Fallback
        
    # 4. Construct the standardized key and check your map
    lookup_key = f"{screen_prefix} {well}"
    
    return pH_map.get(lookup_key, None)
def build_pH_map():
    conn = sqlite3.connect('/home/benne77/2Trig/CrystalDex.db')
    rows = conn.execute("SELECT crystal_screen_id, condition FROM conditions").fetchall()
    conn.close()

    pH_map = {}
    for screen_id, cond in rows:
        cond = clean_condition_string(cond)
        well = re.match(r'^(?:\d+\s+)?([A-H]\d{1,2})\b', cond)
        ph = re.findall(r'\bpH\s+(\d+(?:\.\d+)?)', cond)
        if not well or not ph:
            continue
        pH_map[(SCREENS[screen_id], well.group(1))] = ph[-1]   # "Average pH" comes last

    for (screen, well), val in list(pH_map.items()):           # xtal alias
        if screen == 'crystal screen':
            pH_map[('xtal', well)] = val
    # print(pH_map)
    return pH_map

ALIASES = [
    (r'salt\s*-?\s*rx|slat\s*rx', 'salt rx'),
    (r'peg\s*-?\s*ion',           'peg ion'),
    (r'wizard',                   'wizard screen'),
    (r'crystal\s*screen|xtal',    'crystal screen'),
    (r'\bindex\b',                'index'),
]
# def build_pH_map():
    # pH_map = {} # crystal condition : pH value
    #     #need to adjust crystal screen later because it is also sometimes referred to as 'xtal'
    # conditions_key = {
    #     1: 'crystal screen',
    #     2: 'index',
    #     3: 'peg ion',
    #     4: 'salt rx',
    #     5: 'wizard screen'
    # }
    # # extracting the conditions that have a pH associated with them and then creating a map with the name as the key and just the pH as the value
    # conn_pH_reference = sqlite3.connect('/home/benne77/2Trig/CrystalDex.db')
    # conditions_df = pd.read_sql_query("SELECT condition, GROUP_CONCAT(crystal_screen_id, ', ') as crystal_ids " \
    # "FROM conditions" \
    # " GROUP BY condition"
    # , conn_pH_reference) 
    
    # condition_with_pH_val = [f"{condition} {crystal_ids}" for condition, crystal_ids in zip(conditions_df['condition'], conditions_df['crystal_ids'])
    #                             if 'pH' in condition]
    # condition_with_pH_val = [clean_condition_string(condition) for condition in condition_with_pH_val]
    # # grabbing the pH value from each entry for the map
    # n = 0

    # for condition in condition_with_pH_val:
    #     condition_split = condition.split()
    #     for value in condition_split:
    #         if value == 'pH' and condition_split[n-1] == 'Average':
    #             pH_map[condition] = condition_split[n+1]
    #         elif value == 'pH':
    #             pH_map[condition] = condition_split[n+1]
    #         n += 1
    #     n = 0

    # updated_pH_map = {}

    # for key, val in pH_map.items():
    #     # Find the matching condition
    #     new_key = key  # Default to the old key if no match is found
    #     match_trailing_num = re.search(r'\d+$', key)
    #     if match_trailing_num:
    #         idx = int(match_trailing_num.group()) - 1
    #         for condition_reference, condition in conditions_key.items():
    #             if len(conditions_key) >= idx:
    #                 if condition_reference - 1 == idx:
    #                     well = re.findall(r"[A-Z]\d{1,2}", key, re.IGNORECASE)
    #                     new_key = str(f"{condition} {well[0]}")
    #     updated_pH_map[new_key] = val
    # known_prefixes = ['index', 'peg ion', 'salt rx', 'wizard screen', 'crystal screen']
    # for key, val in pH_map.items():
    #     if any(key.lower().startswith(prefix) for prefix in known_prefixes):
    #         continue
    #     key = key.split()
    #     key = 'crystal screen ' + key[0]
    #     updated_pH_map[key] = val
    #     updated_pH_map['Xtal'] = val
    #     # Store with the new key
    # updated_pH_map['Storage buffer'] = '9.3'
        
    # # Moving to original variable
    # pH_map = updated_pH_map
    # pH_map = get_proper_well(pH_map)
    # print(pH_map)
    # conn_pH_reference.close()
    # return pH_map
def lookup_pH(raw, pH_map):
    s = str(raw)
    low = s.lower().replace('_', ' ')
    if low.strip() == 'storage buffer':
        return '9.3'
    well = re.search(r'\b([a-h]\d{1,2})\b', low)
    if not well:
        return None
    well = well.group(1).upper()
    for pat, name in ALIASES:
        if re.search(pat, low):
            return pH_map.get((name, well))          # exact (screen, well), no guessing
    m = re.search(r'Average\s+pH\s+(\d+(?:\.\d+)?)', s)   # e.g. the 23.0 rows
    return m.group(1) if m else None
def connect_to_database():
    conn_database = sqlite3.connect('/home/benne77/data.db')
    cursor = conn_database.cursor()

    cursor.execute("PRAGMA table_info(data_table)")
    
    columns = [info[1] for info in cursor.fetchall()]

    # Only add the pH column if it's missing
    if 'pH' not in columns:
        cursor.execute("ALTER TABLE data_table ADD COLUMN pH TEXT")
        conn_database.commit()
        print("Column 'pH' added successfully.")
    else:
        print("Column 'pH' already exists, skipping.")

    conn_database.close()
    # if the condition in the database is equal to a condition in the map then make the pH column equal to the corresponding value in the map.
    engine = create_engine('sqlite:////home/benne77/data.db')
    df = pd.read_sql("SELECT * FROM data_table", engine)
    return df, engine

def match_pH():
    pH_map = build_pH_map()
    df, engine = connect_to_database()

    # Variables for below.
     #cc = crystal condition
    cc_known_pH = ''
    well_known_pH = ''
    pH = 0
    n = 0
    num_found = 0
    unknown_pH_conditions = df['crystalcond'].values.tolist()
    # Basically I am going through the crystal conditions in the dataframe and pulling out the raw condition and the well. Getting rid of other junk
    row = 0
    for line in unknown_pH_conditions:
        cc_unknown_pH = ''
        well_unknown_pH = ''
        history = []
        line = str(line)
        if len(line) < 2: continue
        original_line = line
        line = line.split()
        for i in range(len(line)):
            # current_item = line[i]
            # next_item = line[i+1]
            history.append(line[i])
        well_match = re.search(r'\b([A-H]\d{1,2})\b', original_line, re.IGNORECASE)
        well_unknown_pH = well_match.group(1).upper() if well_match else ''

        if not well_unknown_pH:
            row += 1
            continue

        cc_unknown_pH = ' '.join(history) ###### The rest of the stuff in the line.
        matched_before = df.iat[row, df.columns.get_loc('pH')]

    df['pH'] = [lookup_pH(c, pH_map) if pd.notna(c) else None for c in df['crystalcond']]
    df.to_sql('data_table', engine, if_exists='replace', index=False) 
    engine.dispose()

def main():
    match_pH()

if __name__ == "__main__":
    main()
