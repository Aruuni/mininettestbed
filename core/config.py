
import os 

USERNAME = "mihai"
if not USERNAME:
    raise ValueError("You MUST set your username in core/config.py")

HOME_DIR = "/home/mihai"
ORCA_INSTALL_FOLDER =f"{HOME_DIR}/Orca" 
SAGE_INSTALL_FOLDER =f"{HOME_DIR}/sage" 
PCC_USPACE_INSTALL_FOLDER = f"{HOME_DIR}/PCC-Uspace"
PCC_RL_INSTALL_FOLDER = f"{HOME_DIR}/PCC-RL"
ASTRAEA_INSTALL_FOLDER = f"{HOME_DIR}/astraea-open-source" 



# Since the python script is run as root, you need to explicitly provide the user for 
# for user level calls






