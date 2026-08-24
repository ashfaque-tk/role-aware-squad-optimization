""" different formation and playing choices 
"""
FORMATION_STYLES =  {( (4,3,3), 'attack'): {
                            'CAM': (1, 2),  # (min, max)
                            'CM':  (0, 2),
                            'CDM': (0, 1),
                            'LW':  (0, 1),
                            'RW':  (0, 1),
                            'ST':  (0, 1),
                            'CF': (0,1),
                            'CB':  (2, 2),
                            'LB':  (0, 1),'LWB':(0,1),
                            'RB':  (0, 1),'RWB' :(0,1),
                            'LM': (0,1),
                            'RM': (0,1) 
                            },
                    ((4,3,3), 'defend'): {
                            'CAM': (0, 0),  # (min, max)
                            'CM':  (1, 2),
                            'CDM': (1, 2),
                            'LW':  (0, 1),'LWB':(0,1),
                            'RW':  (0, 1),'RWB':(0,1),
                            'ST':  (1, 1),
                            'CF': (0,1),
                            'CB':  (2, 2),
                            'LB':  (0, 1),
                            'RB':  (0, 1),
                            'LM' : (0,1),
                            'RM' :(0,1)  
                            }
                            }      
SLOT_CONFIGS = {(4, 3, 3): {
                            "GK":       ["GK"],
                            "LB_SLOT":  ["LB", "LWB"],
                            "CB_SLOT":  ["CB"],
                            "RB_SLOT":  ["RB", "RWB"],
                            "LCM_SLOT": ["CM", "LM", "CDM", "CAM"],
                            "CCM_SLOT": ["CDM", "CM", "CAM"],
                            "RCM_SLOT": ["CM", "RM", "CDM", "CAM"],
                            "LW_SLOT":  ["LW", "LM", "LF", "ST"],
                            "ST_SLOT":  ["ST", "CF"],
                            "RW_SLOT":  ["RW", "RM", "RF", "ST"],
                        }
                    }

MUTUALLY_EXCLUSIVE_GROUPS = [ ('LB','LWB'),('RB','RWB')]