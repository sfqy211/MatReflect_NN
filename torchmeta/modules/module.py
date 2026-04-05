from torch import nn


class MetaModule(nn.Module):
    def meta_named_parameters(self, prefix: str = "", recurse: bool = True):
        return self.named_parameters(prefix=prefix, recurse=recurse)
