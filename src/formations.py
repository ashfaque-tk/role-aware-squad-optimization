# formation.py

from typing import Dict, Tuple

# role_family -> (min, max)
FormationSpec = Dict[str, Tuple[int, int]]

GLOBAL_ROLE_MAPING: Dict[str,str]= { 'DF':['LB_LWB','CB','RB_RWB'],'MF':['LM','CM_CAM','CDM','RM'],'FW':['LW','ST_CF','RW']}

MICRO_TO_SUBROLE = {
    'LB': 'LB_LWB', 'LWB': 'LB_LWB',
    'RB': 'RB_RWB', 'RWB': 'RB_RWB',
    'CB': 'CB',

    'CDM': 'CDM',
    'CM': 'CM_CAM', 'CAM': 'CM_CAM',
    'LM': 'LM', 'RM': 'RM',

    'LW': 'LW', 'RW': 'RW',
    'CF': 'ST_CF', 'ST': 'ST_CF',
}


FORMATIONS_SPEC: Dict[Tuple[int, int, int], FormationSpec] = {

    (4, 3, 3): {
                'CM_CAM': (1, 2),  # (min, max)
                'CDM': (1, 2),
                'LW':  (1, 1),
                'RW':  (1, 1),
                'ST_CF':  (1, 1),
                # 'CF': (0,1),
                'CB':  (2, 2),
                'LB_LWB':  (1, 1),
                # 'LWB': (0,1),
                'RB_RWB': (1,1),
                # 'RB':  (1, 1),
                'LM': (0,1),
                'RM': (0,1)
    }

}
