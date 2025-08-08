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

# Quick test:


def k_shortest_pseudo_disjoint_paths(original_graph: DiGraph, src, dst, k:int, penalty_mult:float=10):
    """
    Returns a list of tuples representing the k shortest pseudo-disjoint paths.
    Each path found applies a weight penalty along its edges is the graph, making subsequent paths less likely to collide
    Penalty is applied as a multipier: larger values encourage disjoint paths, but even values barely over 1 will make use of any equal-cost paths
    src and dst can be any hashable type representing nodes in the graph
    If any duplicate paths are found, the function returns early. This means there are no more viable paths for the given penalty multiplier.
    """
    graph:DiGraph = original_graph.copy()
    paths:list[tuple] = []
    for i in range(0, k):
        current_path:tuple = tuple(nx.shortest_path(graph, src, dst, "weight"))
        if current_path in paths:
            break
        paths.append(current_path)
        apply_penalty_along_path(graph, current_path, penalty_mult)
    return paths
#(k-shortest, k-shortest-disjoint, k-shortest-pseduo-disjoint, k-equal-cost)

def k_shortest_similar_paths(original_graph: DiGraph, src, dst, k:int, threshold:float=50, penalty_mult:float=500):
    """
    Returns a list of tuples representing the shortest possible combination of k similar-cost paths (within a threshold)
    A penality multipier parameter is provided if disjointedness is not important - however, this defeats the point of this function in most cases
    """
    pass

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