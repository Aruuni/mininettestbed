sudo add-apt-repository -y ppa:jblgf0/python


sysctl net.ipv4.tcp_available_congestion_control
# mininettestbed
Code for the evaluation of RL-based protocols using Mininet

## System requirements
### Operating System
Code has been run on Ubuntu 22.04 LTS with Linux Kernel 6.4.0 (found [here](https://github.com/google/bbr/tree/v3)) which includes bbrv3. 

Using other Linux kernels may be problematic due to:
- Cubic implementation may slightly differ from the one used by Orca, especially the Slow Start phase.


### Python
The Python version used to run core code is python3.7. 
The RL agents of Orca and Aurora run on Python 3.7 also 

## Installation

Run the [install script](./install.sh) to install 

Download [Orca](https://github.com/Aruuni/Orca) and follow the repo's instruction to install it.
Download [PCC-Uspace](https://github.com/giacomoni/PCC-Uspace) and [PCC-RL](https://github.com/giacomoni/PCC-RL) and follow the repo's instruction to install Aurora.


Install python interpreter (3.5) for Orca's agent using venv:

```bash
cd
python3 -m venv venv
```


## Configuration
Set your username in *core/config.py*

```python
USERNAME=None
```

Make sure installation location of Orca, PCC-RL and PCC-Uspace match the path set in core/config.py (home directory)

## Running the experiments
The experiments folder contain one script per experiment. 

To run them all, just execute

```bash
sudo ./run_rexperiments.sh
```

## Data collected
A detailed explanation of the data collected during emulation can be found in the *figshare* database.

## Plotting results
All plots on the paper can be reproduced by running the corresponding script in the plots folder. The scripts assume that results are stored in *mininetestbed/nooffload*.

You can also reproduce the plots without having to rerun the experiment by downloading the dataset available [here](https://sussex.figshare.com/articles/dataset/Data_for_Reinforcement_Learning-based_Congestion_Control_A_Systematic_Evaluation_of_Fairness_Efficiency_and_Responsiveness/24970173). Make sure to move the data into the expected location or change the path(s) in the python scripts
