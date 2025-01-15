# mininettestbed
Code for the evaluation of RL-based protocols using Mininet


## System requirements
### Operating System
Code has been run on Ubuntu 22.04 LTS with Linux Kernel 6.4.0 (found [here](https://github.com/google/bbr/tree/v3)) which includes bbrv3. 

Using other Linux kernels may be problematic due to:
- Cubic implementation may slightly differ from the one used by Orca, especially the Slow Start phase.


### Python
The Python version used to run core code is Python >= 3.7. 
The RL agents of Orca,  Aurora and Astraea run on Python 3.7, sage runs on 3.6.

## Installation

Run the [install script](./install.sh) to install [Orca](https://github.com/Aruuni/Orca), [Astraea](https://github.com/Aruuni/astraea-open-source), [PCC Vivace](https://github.com/PCCproject/PCC-Kernel/tree/vivace) and [sage](https://github.com/Aruuni/sage) (only available on ubuntu 16.04 using the precompiled 4.19 kernel)

```bash
bash install.sh 
```


## Configuration
Set your username in *core/config.py*

```python
USERNAME=None
```

Make sure installation location of Orca, PCC-RL and PCC-Uspace match the path set in core/config.py (home directory)

check for the available kernel conegstion control using: 
```bash 
sysctl net.ipv4.tcp_available_congestion_control
```

## Running the experiments
The experiments folder contain one script per experiment. 

To run them all, just execute

```bash
sudo ./run_rexperiments.sh
```

