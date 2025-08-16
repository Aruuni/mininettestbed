import networkx as nx
from networkx import DiGraph, Graph
import copy

# # Returns the k shortest paths from the given graph. src and dst can be any hashable type representing a node in the graph
# def k_shortest_paths(graph: DiGraph, k:int, src, dst):
#     path_generator = nx.shortest_simple_paths(self.graph, src_ip, dst_ip) # returns a generator that creates shortest paths as requested (sort of like an iterator, does not generate them all at once)
#             k_shortest_paths:list[tuple] = []
#             for p, path in enumerate(path_generator):
#                 self.paths.setdefault(src_ip, {}).setdefault(dst_ip, {}).setdefault(tuple(path), []) # apply shortest paths to dict they do not already exist
#                 if p+1 >= self.NUM_PATHS: 
#                     break

"""
A small library of path acquisition algorithms built on top of networkx.
Not all paths are necessarily shortest - fairness, cost, and disjointedness must all be considered
TODO: Consider adding a function that determines what value of k would produce the best results, given some metrics
"""

# Path selection functions ------------------------------------------------------------------------------------------------------------------------------------------------------
"""
This section contains all of the main path selection algorithms you may want to use.
Each function has many parameters/behaviours/possible use cases. They are broad in scope by design.
These are the functions that will be called by certain presets
"""
def get_shortest_paths(original_graph: DiGraph, src, dst, max_paths=8):
    """
    Returns the list of k-shortest-paths, stopping early if duplicate paths are found
    Does not enforce any sort of disjoint rules or penalties for new paths.
    """
    path_generator = nx.shortest_simple_paths(original_graph, src, dst) # path generator, use next() to get the next shortest path. This is used to avoid computing them all.
    paths:list[tuple] = []
    for i in range(0, max_paths):
        path = tuple(next(path_generator))
        if path == None or path in paths:
            break
        paths.append(path)
    return paths

def shortest_pseudo_disjoint_paths(original_graph: DiGraph, src, dst, max_paths:int, penalty_mult:float=10, shared_penalty_mult:float=1):
    """
    Returns a list of tuples representing the k (max_paths) shortest pseudo-disjoint paths.
    Each path found applies a weight penalty along its edges is the graph, making subsequent paths less likely to collide
    Penalty is applied as a multipier: larger values encourage disjoint paths, values just above 1 lightly encourage disjointedness (makes use of equal-cost paths), and values <=1 will just return a single path
    penalty_mult is applied to a copy of the graph, so only related paths (sibling subflows) will avoid each other
    shared_penalty_mult is applied to the ORIGINAL graph, allowing any future paths (subflows from other connections) to avoid each other
    src and dst can be any hashable type representing nodes in the graph
    If any duplicate paths are found, the function returns early. This means there are no more viable paths for the given penalty multiplier.
    """

    graph:DiGraph = original_graph.copy()

    paths:list[tuple] = []
    for i in range(0, max_paths):
        # Get the next shortest path based on current weights
        try:
            current_path:tuple = tuple(nx.shortest_path(graph, src, dst, "weight"))
        except ValueError:
            # Negative edge weights warning. Networkx doesn't like us changing the graph, but it doesn't cause issues.
            # I'm ignoring the warning to clean up the console.
            pass
        if current_path in paths:
            break
        paths.append(current_path)

        # Apply penalties, if they exist
        if penalty_mult != 1: apply_penalty_along_path(graph, current_path, penalty_mult)
        if shared_penalty_mult != 1: apply_penalty_along_path(original_graph, current_path, shared_penalty_mult)
    print(paths)
    for u, v, data in graph.edges(data=True):
        print(u, v, data.get("weight"))
    return paths

def shortest_similar_paths(original_graph: DiGraph, src, dst, max_paths:int, threshold:float=50, penalty_mult:float=500):
    """
    Returns a list of tuples representing the shortest possible combination of k similar-cost paths (within a threshold)
    A penality multipier parameter is provided if disjointedness is not important - however, this defeats the point of this function in most cases
    """
    # TODO: just all of it bro
    pass

# End of path selection functions ------------------------------------------------------------------------------------------------------------------------------------------------

# Utility functions --------------------------------------------------------------------------------------------------------------------------------------------------------------
"""
Random utility functions that may be generally useful across different path selection algorithms
"""

def apply_penalty_along_path(graph:DiGraph, path:tuple, penalty:float, additive=False):
    """
    Utility function that applies a penalty along edges in a path, either multiplicatively or additively
    """
    for n, node in enumerate(path):
        if n == len(path)-1:
            break
        next_node = path[n+1]
        if additive:
            graph[node][next_node]["weight"] += penalty
        else:
            graph[node][next_node]["weight"] *= penalty

# End of utility functions -------------------------------------------------------------------------------------------------------------------------------------------------------

def get_paths(original_graph: DiGraph, src, dst, preset:str, max_paths=8):
    """
    Returns a list of shortest paths, acquired using some path selection strategy preset
    
    All penalties are at least slightly above one to make use of equal-cost paths.
    Sibling penalties are larger when possible, as intra-subflow collisons promote unfairness. 
    The packet scheduler can cope with inter-subflow collisons if given alternatives.
    """
    if preset == "k-shortest": # Shortest unique paths, no disjointedness enforced
        return get_shortest_paths(original_graph, src, dst, max_paths=max_paths)
    
    elif preset == "all-lightly-disjoint": # Subflows are lightly encouraged to be disjoint to ALL subflows equally
        return shortest_pseudo_disjoint_paths(original_graph, src, dst, max_paths=max_paths, penalty_mult=1.05, shared_penalty_mult=1.05)
    
    elif preset == "all-strongly-disjoint": # Subflows are strongly encouraged to be disjoint to ALL subflows equally
        return shortest_pseudo_disjoint_paths(original_graph, src, dst, max_paths=max_paths, penalty_mult=1000, shared_penalty_mult=1000)
    
    elif preset == "strongly-disjoint-siblings": # Subflows are strongly encouraged to be disjoint to sibling subflows
        return shortest_pseudo_disjoint_paths(original_graph, src, dst, max_paths=max_paths, penalty_mult=1000, shared_penalty_mult=1.05)
    
    elif preset == "strongly-disjoint-strangers": # Subflows are strongly encouraged to be disjoint to stranger subflows (and slightly to each other, or else you would repeatedly be assigned the same path)
        return shortest_pseudo_disjoint_paths(original_graph, src, dst, max_paths=max_paths, penalty_mult=1.05, shared_penalty_mult=1000)
    
    else:
        print(f"ERROR - path selection preset \"{preset}\" does not exist!")
        return NotImplementedError

# End of path selection presets --------------------------------------------------------------------------------------------------------------------------------------------------

"""
List of path selection functions that can be called by external code to acquire paths
Use the presets function instead if you don't care to tweak parameters and just want to test a series of broadly different behaviours
"""
PATH_SELECTORS = {
    'shortest_pseudo_disjoint_paths': shortest_pseudo_disjoint_paths,
}
