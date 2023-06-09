from torch_geometric.nn import GATConv, SAGPooling, GraphConv, GCN2Conv, GCNConv
from torch_geometric.nn import global_mean_pool as gap, global_max_pool as gmp
# from torch_geometric.nn import MessagePassing
import torch.nn as nn
import torch
import torch.nn.functional as F
from .embedding_layer import EmbeddingLayer
from typing import List, Tuple
from .graph_norm import GraphNorm
from torch_geometric.nn.conv import MessagePassing

import math
from typing import Optional, Tuple, Union

import torch
import torch.nn.functional as F
from torch import Tensor
from torch_sparse import SparseTensor

from torch_geometric.nn.conv import MessagePassing
from torch_geometric.nn.dense.linear import Linear
from torch_geometric.typing import Adj, OptTensor, PairTensor
from .mlp_layer import MLPLayer

class BasicGAT(MessagePassing):
    def __init__(self, in_channels, out_channels, heads, concat, dropout, add_self_loops, bias, max_node_per_graph):
        super(BasicGAT, self).__init__()
        self.max_node_per_graph = max_node_per_graph
        self.gatconv = GATConv(in_channels=in_channels,
                               out_channels=out_channels,
                               heads=heads,
                               concat=concat,
                               dropout=dropout,
                               add_self_loops=add_self_loops,
                               bias=bias)
        self.lin1 = nn.Linear(heads*out_channels,out_channels)

        self.norm = GraphNorm(out_channels)
        self.activation = nn.ReLU()

    def forward(self, x, edge, batch_map):
        out = self.gatconv(x, edge)
        out = F.relu(out)
        out = self.lin1(out)
        out = self.norm(out, batch_map)
        #return self.activation(out.view(-1, out.shape[-1]))
        return self.activation(out)


class residual_graph_attention(MessagePassing):
    """deep gat + graph attention pooling
    graph norm + mapping module


    Args:
        MessagePassing ([type]): [description]
    """
    def __init__(self,
                 num_edge_types,
                 in_features,
                 out_features,
                 embedding_out_features,
                 embedding_num_classes,
                 dropout=0,
                 max_node_per_graph=50,
                 model_epoch=6,
                 add_self_loops=False,
                 bias=True,
                 aggr="mean",
                 device="cpu"):
        super(residual_graph_attention, self).__init__(aggr=aggr)
        # params set
        self.device = device
        self.max_node_per_graph = max_node_per_graph
        self.model_epoch = model_epoch
        self.num_edge_types = num_edge_types
        self.dropout= dropout
        self.value_embeddingLayer = EmbeddingLayer(embedding_num_classes,
                                                   in_features,
                                                   embedding_out_features,
                                                   device=device)
        # self.norm = GraphNorm(out_features)  # embedding_norm
        '''
        self.type_embeddingLayer = EmbeddingLayer(embedding_num_classes,
                                                  in_features,
                                                  embedding_out_features,
                                                  device=device)
        '''
        self.MessagePassingNN =  nn.ModuleList([nn.ModuleList([
                GATConv(out_features, out_features//8, heads=8, concat=True, add_self_loops=True)

                for _ in range(self.num_edge_types)
            ]) for __ in range(self.num_edge_types) ])

        self.lin = nn.Linear(in_features=out_features*self.num_edge_types, out_features=out_features)
        

    def forward(self,
                x,
                edge_list: List[torch.tensor],
                batch_map: torch.Tensor,
                **kwargs):
        x_embedding = self.value_embeddingLayer(x)
        
        # add res connection 
        last_node_states = x_embedding
        for layer in range(len(edge_list)):
            # GAT
            out_concat = []
            for e in range(len(edge_list)):
                one_layer_out = self.MessagePassingNN[layer][e](last_node_states, edge_list[e])
                out_concat.append(one_layer_out)
            out_concat = torch.stack(out_concat, dim=0) # E, V, D
            cur_layer_out = torch.mean(out_concat, dim =0) # V, D
            cur_layer_out = F.relu(cur_layer_out)
            last_node_states = torch.mean(torch.stack([last_node_states, cur_layer_out], dim=0), dim=0)
        return last_node_states