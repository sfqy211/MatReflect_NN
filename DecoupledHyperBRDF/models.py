import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import re
from collections import OrderedDict

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
try:
    from torchmeta.modules import MetaModule, MetaSequential
except Exception:
    class MetaModule(nn.Module):
        def meta_named_parameters(self, prefix="", recurse=True):
            return self.named_parameters(prefix=prefix, recurse=recurse)

    class MetaSequential(nn.Sequential, MetaModule):
        def forward(self, input, params=None):
            output = input
            for name, module in self._modules.items():
                subdict = None
                if params is not None:
                    prefix = f"{name}."
                    subdict = OrderedDict(
                        (key[len(prefix):], value) for key, value in params.items() if key.startswith(prefix)
                    )
                if isinstance(module, MetaModule):
                    output = module(output, params=subdict)
                else:
                    output = module(output)
            return output


def get_subdict(params, key):
    if params is None:
        return None
    if key is None:
        return params

    key_escape = re.escape(key)
    key_re = re.compile(r"^{0}\.(.+)".format(key_escape))
    result = OrderedDict()
    for name in params.keys():
        match = key_re.match(name)
        if match is not None:
            result[match.group(1)] = params[name]
    return result


def init_weights_normal(m):
    if type(m) == BatchLinear or type(m) == nn.Linear:
        if hasattr(m, "weight"):
            nn.init.kaiming_normal_(m.weight, a=0.0, nonlinearity="relu", mode="fan_in")


def init_weights_selu(m):
    if type(m) == BatchLinear or type(m) == nn.Linear:
        if hasattr(m, "weight"):
            num_input = m.weight.size(-1)
            nn.init.normal_(m.weight, std=1 / math.sqrt(num_input))


def init_weights_elu(m):
    if type(m) == BatchLinear or type(m) == nn.Linear:
        if hasattr(m, "weight"):
            num_input = m.weight.size(-1)
            nn.init.normal_(m.weight, std=math.sqrt(1.5505188080679277) / math.sqrt(num_input))


def init_weights_xavier(m):
    if type(m) == BatchLinear or type(m) == nn.Linear:
        if hasattr(m, "weight"):
            nn.init.xavier_normal_(m.weight)


class BatchLinear(nn.Linear, MetaModule):
    __doc__ = nn.Linear.__doc__

    def forward(self, input, params=None):
        if params is None:
            params = OrderedDict(self.named_parameters())

        bias = params.get("bias", None)
        weight = params["weight"]
        output = input.matmul(weight.permute(*[i for i in range(len(weight.shape) - 2)], -1, -2))
        output += bias.unsqueeze(-2)
        return output


class FCBlock(MetaModule):
    def __init__(
        self,
        in_features,
        out_features,
        num_hidden_layers,
        hidden_features,
        outermost_linear=False,
        nonlinearity="relu",
        weight_init=None,
    ):
        super().__init__()

        self.first_layer_init = None
        nls_and_inits = {
            "relu": (nn.ReLU(inplace=True), init_weights_normal, None),
            "sigmoid": (nn.Sigmoid(), init_weights_xavier, None),
            "tanh": (nn.Tanh(), init_weights_xavier, None),
            "selu": (nn.SELU(inplace=True), init_weights_selu, None),
            "softplus": (nn.Softplus(), init_weights_normal, None),
            "elu": (nn.ELU(inplace=True), init_weights_elu, None),
        }
        nl, nl_weight_init, first_layer_init = nls_and_inits[nonlinearity]

        self.weight_init = weight_init if weight_init is not None else nl_weight_init

        self.net = [
            MetaSequential(BatchLinear(in_features, hidden_features), nl),
        ]

        for _ in range(num_hidden_layers):
            self.net.append(MetaSequential(BatchLinear(hidden_features, hidden_features), nl))

        if outermost_linear:
            self.net.append(MetaSequential(BatchLinear(hidden_features, out_features)))
        else:
            self.net.append(MetaSequential(BatchLinear(hidden_features, out_features), nl))

        self.net = MetaSequential(*self.net)
        if self.weight_init is not None:
            self.net.apply(self.weight_init)

        if first_layer_init is not None:
            self.net[0].apply(first_layer_init)

    def forward(self, coords, params=None, **kwargs):
        if params is None:
            params = OrderedDict(self.named_parameters())
        return self.net(coords, params=get_subdict(params, "net"))

    def forward_with_activations(self, coords, params=None, retain_grad=False):
        if params is None:
            params = OrderedDict(self.named_parameters())

        activations = OrderedDict()
        x = coords.clone().detach().requires_grad_(True)
        activations["input"] = x
        for i, layer in enumerate(self.net):
            subdict = get_subdict(params, "net.%d" % i)
            for j, sublayer in enumerate(layer):
                if isinstance(sublayer, BatchLinear):
                    x = sublayer(x, params=get_subdict(subdict, "%d" % j))
                else:
                    x = sublayer(x)
                if retain_grad:
                    x.retain_grad()
                activations["_".join((str(sublayer.__class__), "%d" % i))] = x
        return activations


class SetEncoder(nn.Module):
    def __init__(self, in_features, out_features, num_hidden_layers, hidden_features, nonlinearity="relu", pooling="mean"):
        super().__init__()
        assert nonlinearity in ["relu"], "Unknown nonlinearity type"
        assert pooling in ["mean", "meanmax"], "Unknown pooling type"

        self.pooling = pooling
        nl = nn.ReLU(inplace=True)
        weight_init = init_weights_normal

        self.net = [nn.Linear(in_features, hidden_features), nl]
        self.net.extend(
            [nn.Sequential(nn.Linear(hidden_features, hidden_features), nl) for _ in range(num_hidden_layers)]
        )
        self.net.extend([nn.Linear(hidden_features, out_features), nl])
        self.net = nn.Sequential(*self.net)
        self.net.apply(weight_init)
        self.out_features = out_features if pooling == "mean" else out_features * 2

    def forward(self, context_x, context_y, **kwargs):
        input_tensor = torch.cat((context_x, context_y), dim=-1)
        embeddings = self.net(input_tensor)
        if self.pooling == "mean":
            return embeddings.mean(dim=-2)
        mean_embed = embeddings.mean(dim=-2)
        max_embed = embeddings.max(dim=-2).values
        return torch.cat((mean_embed, max_embed), dim=-1)


class HyperNetwork(nn.Module):
    def __init__(self, hyper_in_features, hyper_hidden_layers, hyper_hidden_features, hypo_module):
        super().__init__()

        hypo_parameters = hypo_module.meta_named_parameters()
        self.names = []
        self.nets = nn.ModuleList()
        self.param_shapes = []
        for name, param in hypo_parameters:
            self.names.append(name)
            self.param_shapes.append(param.size())

            hn = FCBlock(
                in_features=hyper_in_features,
                out_features=int(torch.prod(torch.tensor(param.size()))),
                num_hidden_layers=hyper_hidden_layers,
                hidden_features=hyper_hidden_features,
                outermost_linear=True,
                nonlinearity="relu",
            )
            self.nets.append(hn)

            if "weight" in name:
                self.nets[-1].net[-1].apply(lambda module: hyper_weight_init(module, param.size()[-1]))
            elif "bias" in name:
                self.nets[-1].net[-1].apply(lambda module: hyper_bias_init(module))

    def set_output_bias(self, name, value):
        if name not in self.names:
            return
        idx = self.names.index(name)
        final_linear = self.nets[idx].net[-1][0]
        if hasattr(final_linear, "bias") and final_linear.bias is not None:
            with torch.no_grad():
                final_linear.bias.fill_(value)

    def forward(self, z):
        params = OrderedDict()
        for name, net, param_shape in zip(self.names, self.nets, self.param_shapes):
            batch_param_shape = (-1,) + param_shape
            params[name] = net(z).reshape(batch_param_shape)
        return params


class SingleBVPNet(MetaModule):
    def __init__(
        self,
        out_features=1,
        type="relu",
        in_features=2,
        mode="mlp",
        hidden_features=256,
        num_hidden_layers=3,
        outermost_linear=False,
        **kwargs,
    ):
        super().__init__()
        self.mode = mode
        self.net = FCBlock(
            in_features=in_features,
            out_features=out_features,
            num_hidden_layers=num_hidden_layers,
            hidden_features=hidden_features,
            outermost_linear=outermost_linear,
            nonlinearity=type,
        )

    def forward(self, model_input, params=None):
        if params is None:
            params = OrderedDict(self.named_parameters())

        coords_org = model_input["coords"].clone().detach().requires_grad_(True)
        output = self.net(coords_org, get_subdict(params, "net"))
        return {"model_in": coords_org, "model_out": output}

    def forward_with_activations(self, model_input):
        coords = model_input["coords"].clone().detach().requires_grad_(True)
        activations = self.net.forward_with_activations(coords)
        return {"model_in": coords, "model_out": activations.popitem(), "activations": activations}


def hyper_weight_init(m, in_features_main_net):
    if hasattr(m, "weight"):
        nn.init.kaiming_normal_(m.weight, a=0.0, nonlinearity="relu", mode="fan_in")
        m.weight.data = m.weight.data / 1.0e2

    if hasattr(m, "bias"):
        with torch.no_grad():
            m.bias.uniform_(-1 / in_features_main_net, 1 / in_features_main_net)


def hyper_bias_init(m):
    if hasattr(m, "weight"):
        nn.init.kaiming_normal_(m.weight, a=0.0, nonlinearity="relu", mode="fan_in")
        m.weight.data = m.weight.data / 1.0e2

    if hasattr(m, "bias"):
        fan_in, _ = nn.init._calculate_fan_in_and_fan_out(m.weight)
        with torch.no_grad():
            m.bias.uniform_(-1 / fan_in, 1 / fan_in)


def _normalize(v, eps=1e-6):
    return v / torch.clamp(v.norm(dim=-1, keepdim=True), min=eps)


def _dot(v1, v2):
    return (v1 * v2).sum(dim=-1, keepdim=True)


def _rotate_vector(v, axis, angle):
    axis = _normalize(axis)
    cos_angle = torch.cos(angle)
    sin_angle = torch.sin(angle)
    return v * cos_angle + axis * _dot(axis, v) * (1 - cos_angle) + torch.cross(axis, v, dim=-1) * sin_angle


def hd_to_io_torch(half, diff):
    theta_h = torch.atan2(torch.sqrt(torch.clamp(half[..., 0:1] ** 2 + half[..., 1:2] ** 2, min=0.0)), half[..., 2:3])
    phi_h = torch.atan2(half[..., 1:2], half[..., 0:1])

    y_axis = torch.zeros_like(half)
    y_axis[..., 1] = 1.0
    z_axis = torch.zeros_like(half)
    z_axis[..., 2] = 1.0

    tmp = _rotate_vector(diff, y_axis, theta_h)
    wi = _normalize(_rotate_vector(tmp, z_axis, phi_h))
    wo = _normalize(2 * _dot(wi, half) * half - wi)
    return wi, wo


def ggx_smith_g1(n_dot_v, roughness):
    roughness = torch.clamp(roughness, min=1e-4)
    k = ((roughness + 1.0) ** 2) / 8.0
    return n_dot_v / (n_dot_v * (1.0 - k) + k + 1e-6)


def analytic_param_dim(analytic_lobes):
    return 3 + 6 * analytic_lobes


def unpack_analytic_params(analytic_params):
    if isinstance(analytic_params, dict):
        if "lobes" in analytic_params:
            return analytic_params
        return {
            "diffuse_color": analytic_params["diffuse_color"],
            "lobes": [
                {
                    "specular_color": analytic_params["specular_color"],
                    "roughness": analytic_params["roughness"],
                    "specular_scale": analytic_params["specular_scale"],
                    "ior": analytic_params["ior"],
                }
            ],
            "analytic_lobes": 1,
        }

    return {
        "diffuse_color": analytic_params[..., 0:3],
        "lobes": [
            {
                "specular_color": analytic_params[..., 3:6],
                "roughness": analytic_params[..., 6:7],
                "specular_scale": analytic_params[..., 7:8],
                "ior": analytic_params[..., 8:9],
            }
        ],
        "analytic_lobes": 1,
    }


def analytic_param_tensor_to_dict(raw_params, analytic_lobes=1):
    diffuse_color = F.softplus(raw_params[..., 0:3])
    lobes = []
    for lobe_idx in range(analytic_lobes):
        offset = 3 + lobe_idx * 6
        lobes.append(
            {
                "specular_color": torch.sigmoid(raw_params[..., offset : offset + 3]) * 1.5,
                "roughness": 0.02 + 0.88 * torch.sigmoid(raw_params[..., offset + 3 : offset + 4]),
                "specular_scale": F.softplus(raw_params[..., offset + 4 : offset + 5]),
                "ior": 1.02 + 1.98 * torch.sigmoid(raw_params[..., offset + 5 : offset + 6]),
            }
        )
    return {
        "diffuse_color": diffuse_color,
        "lobes": lobes,
        "analytic_lobes": analytic_lobes,
    }


def normalize_brdf_from_median(brdf, median_vals, eps=0.002):
    if median_vals is None:
        return brdf
    return torch.log1p((brdf + eps) / (median_vals + eps))


def eval_analytic_brdf(coords, analytic_params, median_vals=None):
    params = unpack_analytic_params(analytic_params)
    half = _normalize(coords[..., 0:3])
    diff = _normalize(coords[..., 3:6])
    wi, wo = hd_to_io_torch(half, diff)

    n_dot_h = torch.clamp(half[..., 2:3], min=1e-5, max=1.0)
    n_dot_wi = torch.clamp(wi[..., 2:3], min=1e-5, max=1.0)
    n_dot_wo = torch.clamp(wo[..., 2:3], min=1e-5, max=1.0)
    wi_dot_h = torch.clamp(_dot(wi, half), min=1e-5, max=1.0)

    specular = 0.0
    for lobe in params["lobes"]:
        roughness = lobe["roughness"]
        alpha = roughness ** 2
        alpha2 = alpha ** 2

        denom = (n_dot_h ** 2) * (alpha2 - 1.0) + 1.0
        d_term = alpha2 / (math.pi * denom ** 2 + 1e-6)
        g_term = ggx_smith_g1(n_dot_wi, roughness) * ggx_smith_g1(n_dot_wo, roughness)

        ior = lobe["ior"]
        f0 = ((ior - 1.0) / (ior + 1.0)) ** 2
        fresnel = f0 + (1.0 - f0) * ((1.0 - wi_dot_h) ** 5)
        specular = specular + lobe["specular_color"] * lobe["specular_scale"] * (d_term * g_term * fresnel) / (
            4.0 * n_dot_wi * n_dot_wo + 1e-6
        )
    diffuse = params["diffuse_color"]
    brdf = diffuse + specular
    return normalize_brdf_from_median(brdf, median_vals)


class AnalyticBRDFHead(nn.Module):
    def __init__(self, in_features, hidden_features=128, analytic_lobes=1):
        super().__init__()
        self.analytic_lobes = analytic_lobes
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_features),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_features, hidden_features),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_features, analytic_param_dim(analytic_lobes)),
        )
        self.net.apply(init_weights_normal)

    def forward(self, embedding):
        return analytic_param_tensor_to_dict(self.net(embedding), analytic_lobes=self.analytic_lobes)


class HyperBRDF(nn.Module):
    def __init__(self, in_features, out_features, encoder_nl="relu"):
        super().__init__()
        latent_dim = 40
        self.model_type = "baseline"
        self.hypo_net = SingleBVPNet(out_features=out_features, hidden_features=60, type="relu", in_features=6)
        self.hyper_net = HyperNetwork(
            hyper_in_features=latent_dim,
            hyper_hidden_layers=10,
            hyper_hidden_features=128,
            hypo_module=self.hypo_net,
        )
        self.set_encoder = SetEncoder(
            in_features=9,
            out_features=latent_dim,
            num_hidden_layers=2,
            hidden_features=128,
            nonlinearity=encoder_nl,
            pooling="mean",
        )

    def freeze_hypernet(self):
        for param in self.hyper_net.parameters():
            param.requires_grad = False

    def forward(self, model_input):
        amps, coords = model_input["amps"], model_input["coords"]

        if "context_coords" in model_input and "context_amps" in model_input:
            enc_coords = model_input["context_coords"]
            enc_amps = model_input["context_amps"]
        else:
            enc_coords = coords
            enc_amps = amps

        embedding = self.set_encoder(enc_coords, enc_amps)
        hypo_params = self.hyper_net(embedding)
        model_output = self.hypo_net(model_input, params=hypo_params)

        return {
            "model_in": model_output["model_in"],
            "model_out": model_output["model_out"],
            "latent_vec": embedding,
            "hypo_params": hypo_params,
        }


class DecoupledHyperBRDF(nn.Module):
    def __init__(
        self,
        in_features,
        out_features,
        encoder_nl="relu",
        latent_dim=40,
        gate_bias_init=-2.0,
        analytic_lobes=1,
    ):
        super().__init__()
        self.model_type = "decoupled"
        self.latent_dim = latent_dim
        self.gate_bias_init = gate_bias_init
        self.analytic_lobes = analytic_lobes

        self.set_encoder = SetEncoder(
            in_features=9,
            out_features=latent_dim,
            num_hidden_layers=2,
            hidden_features=128,
            nonlinearity=encoder_nl,
            pooling="meanmax",
        )
        self.shared_trunk = nn.Sequential(
            nn.Linear(self.set_encoder.out_features, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, latent_dim),
            nn.ReLU(inplace=True),
        )
        self.shared_trunk.apply(init_weights_normal)

        self.analytic_head = AnalyticBRDFHead(latent_dim, hidden_features=128, analytic_lobes=analytic_lobes)

        self.residual_hypo_net = SingleBVPNet(
            out_features=out_features,
            hidden_features=60,
            type="relu",
            in_features=in_features,
            outermost_linear=True,
        )
        self.residual_hyper_net = HyperNetwork(
            hyper_in_features=latent_dim,
            hyper_hidden_layers=10,
            hyper_hidden_features=128,
            hypo_module=self.residual_hypo_net,
        )

        self.gate_hypo_net = SingleBVPNet(
            out_features=1,
            hidden_features=40,
            type="relu",
            in_features=in_features,
            outermost_linear=True,
        )
        self.gate_hyper_net = HyperNetwork(
            hyper_in_features=latent_dim,
            hyper_hidden_layers=6,
            hyper_hidden_features=96,
            hypo_module=self.gate_hypo_net,
        )
        self.gate_hyper_net.set_output_bias("net.4.0.bias", gate_bias_init)

    def encode_context(self, model_input):
        coords = model_input["context_coords"] if "context_coords" in model_input else model_input["coords"]
        amps = model_input["context_amps"] if "context_amps" in model_input else model_input["amps"]
        embedding = self.set_encoder(coords, amps)
        return self.shared_trunk(embedding)

    def forward(self, model_input):
        branch_latent = self.encode_context(model_input)
        analytic_params = self.analytic_head(branch_latent)

        residual_hypo_params = self.residual_hyper_net(branch_latent)
        residual_raw = self.residual_hypo_net(model_input, params=residual_hypo_params)
        residual_out = F.softplus(residual_raw["model_out"])

        gate_hypo_params = self.gate_hyper_net(branch_latent)
        gate_raw = self.gate_hypo_net(model_input, params=gate_hypo_params)
        gate_out = torch.sigmoid(gate_raw["model_out"])

        analytic_out = eval_analytic_brdf(
            residual_raw["model_in"],
            analytic_params,
            median_vals=model_input.get("median_vals"),
        )
        model_out = analytic_out + gate_out * residual_out

        return {
            "model_in": residual_raw["model_in"],
            "model_out": model_out,
            "analytic_out": analytic_out,
            "residual_out": residual_out,
            "gate_out": gate_out,
            "latent_vec": branch_latent,
            "analytic_params": analytic_params,
            "residual_hypo_params": residual_hypo_params,
            "gate_hypo_params": gate_hypo_params,
            "hypo_params": residual_hypo_params,
        }
