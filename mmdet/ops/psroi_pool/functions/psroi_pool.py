import torch
from torch.autograd import Function
from torch.autograd.function import once_differentiable
from .. import psroi_pool_cuda


class PSRoIPoolingFunction(Function):

    @staticmethod
    def forward(ctx, features, rois, pooled_size, spatial_scale, group_size):
        # pooled_size:池化后结果为pooled_size*pooled_size的，eg.7*7
        # group_size:输入的channel为p*group_size*group_size，eg.10*7*7
        if isinstance(pooled_size, int):
            pooled_height = pooled_size
            pooled_width = pooled_size
        elif isinstance(pooled_size, tuple):
            assert len(pooled_size) == 2
            assert isinstance(pooled_size[0], int)
            assert isinstance(pooled_size[1], int)
            pooled_height, pooled_width = pooled_size
        else:
            raise TypeError(
                '"pooled_size" must be an integer or tuple of integers')
        num_rois = rois.size(0)
        in_channels = features.size(1)
        assert in_channels % group_size**2 == 0
        out_channels = in_channels // group_size**2

        out_size = (num_rois, out_channels, pooled_height, pooled_width)
        output = features.new_zeros(*out_size)
        mapping_channel = features.new_zeros(*out_size, dtype=torch.int)

        psroi_pool_cuda.forward(features, rois, pooled_height, pooled_width,
                                   spatial_scale, group_size, out_channels,
                                   output, mapping_channel)

        ctx.save_for_backward(rois)
        ctx.spatial_scale = spatial_scale
        ctx.feature_size = features.size()
        ctx.mapping_channel = mapping_channel

        return output

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_output):
        rois = ctx.saved_tensors[0]
        spatial_scale = ctx.spatial_scale
        feature_size = ctx.feature_size
        mapping_channel = ctx.mapping_channel
        assert (feature_size is not None and grad_output.is_cuda)

        grad_input = grad_rois = None
        if ctx.needs_input_grad[0]:
            grad_input = grad_output.new_zeros(feature_size)
            psroi_pool_cuda.backward(grad_output, rois, mapping_channel,
                                        spatial_scale, grad_input)

        return grad_input, grad_rois, None, None, None


psroi_pool = PSRoIPoolingFunction.apply
