#include <torch/torch.h>

#include <vector>

std::vector<at::Tensor> top_pool_forward(
    at::Tensor input
) {
    // Initialize output
    at::Tensor output = at::zeros_like(input);

    // Get height
    int64_t height = input.size(2);

    output.copy_(input);

    for (int64_t ind = 1; ind < height; ind <<= 1) {
        at::Tensor max_temp = at::slice(output, 2, 0, height-ind);
        at::Tensor cur_temp = at::slice(output, 2, 0, height-ind);
        at::Tensor next_temp = at::slice(output, 2, ind, height);
        at::max_out(max_temp, cur_temp, next_temp);
    }

    return { 
        output
    };
}

std::vector<at::Tensor> top_pool_backward(
    at::Tensor input,
    at::Tensor grad_output
) {
    auto output = at::zeros_like(input);

    int32_t batch   = input.size(0);
    int32_t channel = input.size(1);
    int32_t height  = input.size(2);
    int32_t width   = input.size(3);

    auto max_val = torch::zeros({batch, channel, width}, at::device(at::kCUDA).dtype(at::kFloat));
    auto max_ind = torch::zeros({batch, channel, width}, at::device(at::kCUDA).dtype(at::kLong));

    auto input_temp = input.select(2, height - 1);
    max_val.copy_(input_temp);

    max_ind.fill_(height - 1);

    auto output_temp      = output.select(2, height - 1);
    auto grad_output_temp = grad_output.select(2, height - 1);
    output_temp.copy_(grad_output_temp);

    auto un_max_ind = max_ind.unsqueeze(2);
    auto gt_mask    = torch::zeros({batch, channel, width}, at::device(at::kCUDA).dtype(at::kByte));
    auto max_temp   = torch::zeros({batch, channel, width}, at::device(at::kCUDA).dtype(at::kFloat));
    for (int32_t ind = 1; ind < height; ++ind) {
        input_temp = input.select(2, height - ind - 1);
        at::gt_out(gt_mask, input_temp, max_val);

        at::masked_select_out(max_temp, input_temp, gt_mask);
        max_val.masked_scatter_(gt_mask, max_temp);
        max_ind.masked_fill_(gt_mask, height - ind - 1);

        grad_output_temp = grad_output.select(2, height - ind - 1).unsqueeze(2);
        output.scatter_add_(2, un_max_ind, grad_output_temp);
    }

    return {
        output
    };
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def(
        "forward", &top_pool_forward, "Top Pool Forward",
        py::call_guard<py::gil_scoped_release>()
    );
    m.def(
        "backward", &top_pool_backward, "Top Pool Backward",
        py::call_guard<py::gil_scoped_release>()
    );
}
