import os 

if "SUDO_USER" in os.environ:
    USERNAME = os.environ["SUDO_USER"]
    HOME_DIR = os.path.expanduser(f"~{USERNAME}")
else:
    HOME_DIR = os.path.expanduser("~")
    USERNAME = os.path.basename(HOME_DIR)

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go one level up
ORCA_INSTALL_FOLDER = f"{PARENT_DIR}/CC/Orca" 
SAGE_INSTALL_FOLDER = f"{PARENT_DIR}/CC/sage" 
PCC_USPACE_INSTALL_FOLDER = f"{PARENT_DIR}/CC/PCC-Uspace"
PCC_RL_INSTALL_FOLDER = f"{PARENT_DIR}/CC/PCC-RL"
ASTRAEA_INSTALL_FOLDER = f"{PARENT_DIR}/CC/astraea-open-source"
LEOEM_INSTALL_FOLDER = f"{PARENT_DIR}/experiments_mininet/LeoEM"

