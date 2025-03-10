import torch
from torch.autograd import gradcheck

import os.path as osp
import sys
sys.path.append(osp.abspath(osp.join(__file__, '../../')))
from psroi_pool import PSRoIPool  # noqa: E402

feat = torch.randn(4, 64, 15, 15, requires_grad=True).cuda()
rois = torch.Tensor([[0, 0, 0, 50, 50], [0, 10, 30, 43, 55],
                     [1, 67, 40, 110, 120]]).cuda()
inputs = (feat, rois)
print('Gradcheck for psroi pooling...')
test = gradcheck(PSRoIPool(4, 1.0 / 8, 4), inputs, eps=1e-5, atol=1e-2)
print(test)
