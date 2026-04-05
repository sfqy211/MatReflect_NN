from collections import OrderedDict

from torch import nn

from .module import MetaModule


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
