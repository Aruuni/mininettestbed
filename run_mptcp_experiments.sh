source common.sh
bash setup.sh
# Testing number of subflows against RTT/Goodput/Fairness in a heavily congested network
# Experiment parameters (when/where/how will hosts/switches/routers connect?)
EXPERIMENTS="multipath/experiment_manhattan_wrapped_random_flooded multipath/experiment_manhattan_random_flooded"         # Which experiment script to run (mininettestbed/experiments_mininet/custom)
SEEDS="1122311 5737537 7342774 274337242 234772"                    # Random seed - random experiments with same seed can be directly compared
FLOWS="8"                                           # number of connections
MESH_SIZES="4"                                      # Manhattan topology only - size of the mesh

# Network Conditions (what external restrictions will be imposed on packets that enter the network?)
BANDWIDTHS="10"
DELAYS="50"                                         # Average delay from client to server
LOSS="0"                                            # 0.0 to 1.0
QMULTS=".2"                                          # What the queue sizes should be relative to the BDP (or local bdp for a given hop?)

# Controller/routing parameters (how will packets be routed through the given topology/conditons?)
CONTROLLERS="multipath_switch"                      # What OpenFlow controller script to use (mininettestbed/controllers/{controller}.py)
PATH_SELECTORS="preset"                             # Which path selector to use. Use "preset" if you want to ignore parameters and just call from a selection of presets
NUM_PATHS="4"                                       # Max number of paths to create per connections. Subflows will be striped across them. 
PATH_PENALTY="10"                                   # How much already-used paths should have their weights penalized during path selection
PATH_SELECTOR_PRESETS="k-shortest all-lightly-disjoint all-strongly-disjoint strongly-disjoint-siblings strongly-disjoint-strangers" # "k-shortest all-lightly-disjoint all-strongly-disjoint strongly-disjoint-siblings strongly-disjoint-strangers"
AQM="fifo"                                          # Queuing disciplines

# Protocol parameters (How will connections respond to the given topology/conditions/routes?)
PROTOCOLS="cubic"                               # List of protocols to use (for MPTCP, each subflow individually use the specified protocol)
SUBFLOWS="1 2 4 8"                      # number of subflows per connection (1 is normal, >1 is MPTCP)

# Misc
RUNS="1"                                            # Number of repeat experiments
OUTPUT_FOLDER="JRA_Poster_Experiments_2"              # for keeping a particular run of experiments separate. "mininet" is the default.

for seed in $SEEDS
do
    for experiment in $EXPERIMENTS
    do
        for bw in $BANDWIDTHS
        do
            for del in $DELAYS
            do
                for qmult in $QMULTS
                do
                    for flow in $FLOWS
                    do
                        for loss in $LOSS
                        do
                            for subflow in $SUBFLOWS
                            do
                                for mesh_size in $MESH_SIZES
                                do
                                    for protocol in $PROTOCOLS
                                    do
                                        for aqm in $AQM
                                        do
                                            for controller in $CONTROLLERS
                                            do
                                                for path_selector in $PATH_SELECTORS
                                                do
                                                    for path_selector_preset in $PATH_SELECTOR_PRESETS
                                                    do
                                                        for num_paths in $NUM_PATHS
                                                        do
                                                            for path_penalty in $PATH_PENALTY
                                                            do
                                                                for run in $RUNS
                                                                do  
                                                                    sudo mn -c
                                                                    run experiments_mininet/$experiment.py $del $bw $qmult $protocol $run $AQM $loss $flow $subflow $mesh_size $controller $seed $path_selector $num_paths $path_penalty $path_selector_preset $OUTPUT_FOLDER
                                                                done
                                                            done
                                                        done
                                                    done
                                                done
                                            done
                                        done
                                    done
                                done
                            done
                        done
                    done
                done
            done
        done
    done
done