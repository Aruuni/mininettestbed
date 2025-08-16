import matplotlib.pyplot as plt
import networkx as nx
import math

def grid_pos(num_nodes):
    side = int(math.sqrt(num_nodes))
    pos = {}
    for i in range(num_nodes):
        row = i // side
        col = i % side
        pos[i] = (col, -row)  # negative row so it plots top to bottom
    return pos

colors_list = [
                    ["#1f77bf", "#4eb4d3", "#799cf3", "#2f8ea1", "#80a8ff", "#67a6c5", "#6167a6", "#5191D1", ],
                    ["#ff7f0e", "#e58a28", "#f3b679", "#e47724", "#ff9e80", "#ff792b", "#d28c30", "#E37A25", ],
                    ["#2ca02c", "#5aeb92", "#74AA36", "#378D26", "#389e47", "#42d6a4", "#74A929", "#64e17f", ],
                    ["#d6272b", "#d34e4e", "#f37f79", "#a1352f", "#ff8780", "#c56b67", "#a66561", "#732525", ],
                    ["#9467bd", "#da7ed7", "#e825e2", "#e654b0", "#e156bc", "#eb67bb", "#952795", "#b429a1", ],
                    ["#8c564b", "#3d1c0a", "#320808", "#402F16", "#433514", "#383508", "#422008", "#3f2b0d", ],
                    ["#e377c2"],
                    ["#7f7f7f"],
                    ["#bcbd22"],
                    ["#17becf"],
                ]
G = nx.grid_2d_graph(4, 4)  # 4x4 grid
G = nx.convert_node_labels_to_integers(G) 
for n, node in enumerate(G.nodes()):
        G.nodes[node]['color'] = colors_list[n%len(colors_list)][0]
colors = [G.nodes[n]['color'] for n in G.nodes()]

pos = nx.spring_layout(G, iterations=100, seed=39775)
pos = grid_pos(16)

# Create a 2x2 subplot
fig, ax = plt.subplots()

nx.draw_networkx_nodes(G, pos, ax=ax)
#nx.draw_networkx_edges(G, pos, ax=ax)

# Draw edges multiple times with different colors and slight offsets (using connectionstyle)
colors = ['red', 'blue', "green", "yellow", "purple", "pink", "brown", "green", "green"]

line_width = 1
line_spread = line_width * .014
global_line_offset = .01
line_alpha = 1
for i, color in enumerate(colors):
    nx.draw_networkx_edges(
        G, pos,
        edgelist=G.edges(),
        edge_color=color,
        width=line_width,
        alpha=line_alpha,
        arrows=True,
        # connectionstyle=f'arc3,rad={0.05 * (i - 0.5)}'  # offset edges with small curve radius
        #connectionstyle=f'bar,fraction={line_spread*(i+1)-line_spread*len(colors)/2 - global_line_offset}'
        connectionstyle=f'bar,fraction={.01}'
        # connectionstyle=f'arc,angleA=20, angleB=20, armA=10, armB=10, rad=20'
        # connectionstyle=f'bar,fraction={i*.017}'
        # connectionstyle=f'bar,fraction={i*.017}'
    )

#plt.show()
plt.savefig("/home/james/networkx_plots/plot_Test.pdf")
print("Output to: /home/james/networkx_plots/plot_Test.pdf")


