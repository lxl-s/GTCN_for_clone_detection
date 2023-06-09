import random
import numpy as np
import torch
from typing import List



def set_seed(args):
    # use for controlling seeds.
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    
    # if args.n_gpu > 0:
    #     torch.cuda.manual_seed_all(args.seed)
    

    