#include <torch/extension.h>

#include <cmath>
#include <vector>

int RROIAlignForwardLaucher(const at::Tensor features, const at::Tensor rois,
                            const float spatial_scale, const int sample_num,
                            const int channels, const int height,
                            const int width, const int num_rois,
                            const int pooled_height, const int pooled_width,
                            at::Tensor output);

int RROIAlignBackwardLaucher(const at::Tensor top_grad, const at::Tensor rois,
                                   const float spatial_scale, const int sample_num,
                                   const int channels, const int height,
                                   const int width, const int num_rois,
                                   const int pooled_height, const int pooled_width,
                                   at::Tensor bottom_grad);

#define CHECK_CUDA(x) TORCH_CHECK(x.type().is_cuda(), #x, " must be a CUDAtensor ")
#define CHECK_CONTIGUOUS(x) \
  TORCH_CHECK(x.is_contiguous(), #x, " must be contiguous ")
#define CHECK_INPUT(x) \
  CHECK_CUDA(x);       \
  CHECK_CONTIGUOUS(x)

int rroi_align_forward_cuda(at::Tensor features, at::Tensor rois,
                           int pooled_height, int pooled_width,
                           float spatial_scale, int sample_num,
                           at::Tensor output) {
  CHECK_INPUT(features);
  CHECK_INPUT(rois);
  CHECK_INPUT(output);

  // Number of ROIs
  int num_rois = rois.size(0);
  int size_rois = rois.size(1);

  if (size_rois != 6) {
    printf("wrong roi size\n");
    return 0;
  }

  int num_channels = features.size(1);
  int data_height = features.size(2);
  int data_width = features.size(3);

  RROIAlignForwardLaucher(features, rois, spatial_scale, sample_num,
                         num_channels, data_height, data_width, num_rois,
                         pooled_height, pooled_width, output);

  return 1;
}

int rroi_align_backward_cuda(at::Tensor top_grad, at::Tensor rois,
                            int pooled_height, int pooled_width,
                            float spatial_scale, int sample_num,
                            at::Tensor bottom_grad) {
  CHECK_INPUT(top_grad);
  CHECK_INPUT(rois);
  CHECK_INPUT(bottom_grad);

  // Number of ROIs
  int num_rois = rois.size(0);
  int size_rois = rois.size(1);
  if (size_rois != 6) {
    printf("wrong roi size\n");
    return 0;
  }

  int num_channels = bottom_grad.size(1);
  int data_height = bottom_grad.size(2);
  int data_width = bottom_grad.size(3);

  RROIAlignBackwardLaucher(top_grad, rois, spatial_scale, sample_num,
                          num_channels, data_height, data_width, num_rois,
                          pooled_height, pooled_width, bottom_grad);

  return 1;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
  m.def("forward", &rroi_align_forward_cuda, "Roi_Align_Rotated forward (CUDA)");
  m.def("backward", &rroi_align_backward_cuda, "Roi_Align_Rotated backward (CUDA)");
}
