from torch_geometric.nn import GATConv, SAGPooling, GCNConv, TransformerConv
from torch_geometric.nn import global_mean_pool as gap, global_max_pool as gmp
from torch_geometric.nn import MessagePassing
from torch_geometric.nn.conv.gcn_conv import GCNConv
import torch.nn as nn
import torch
import torch.nn.functional as F
from typing import List, Tuple

 
from .embedding_layer import EmbeddingLayer  
from .mlp_layer import MLPLayer


class Transformer_GCN(MessagePassing):
    def __init__(
        self,
        num_edge_types,
        in_features,
        out_features,
        embedding_out_features,
        embedding_num_classes,
        dropout=0,
        add_self_loops=False,
        bias=True,
        aggr="mean",
        device="cpu",
    ):
        super(Transformer_GCN, self).__init__(aggr=aggr)
        # params set
        self.num_edge_types = num_edge_types
        self.device = device
        self.dropout = dropout
        self.value_embeddingLayer = EmbeddingLayer(embedding_num_classes,
                                                   in_features,
                                                   embedding_out_features,
                                                   device=device)

        self.MessagePassingNN = nn.ModuleList([
            TransformerConv(in_channels=embedding_out_features, out_channels=out_features//8, heads=8, concat=True)            for _ in range(self.num_edge_types)
        ])


    def forward(self,
                x,
                edge_list: List[torch.tensor],
                batch_map: torch.Tensor,
                **kwargs):
        x_embedding = self.value_embeddingLayer(x)
        last_node_states = x_embedding
        cur_node_states = F.dropout(last_node_states, self.dropout, training=self.training)
        out_list = []
        for i in range(len(edge_list)):
            edge = edge_list[i]
            if edge.shape[0] != 0:
                out_list.append(self.MessagePassingNN[i](cur_node_states, edge))
        cur_node_states = sum(out_list)

        out = cur_node_states
        return out