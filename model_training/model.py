import torch
import torch.nn as nn
import torchvision.models as models


class CrowdCountingModel(nn.Module):
    """
    Improved crowd counting model using pretrained VGG16 frontend.
    VGG16 was pretrained on ImageNet (1.2M images) giving us
    powerful feature extraction for free.
    
    This is the standard approach in crowd counting research
    and what CSRNet, SANet, and other papers use.
    """

    def __init__(self, pretrained=True):
        super(CrowdCountingModel, self).__init__()

        # Load VGG16 pretrained on ImageNet
        # We only use the first 23 layers (up to pool3)
        vgg = models.vgg16(weights='DEFAULT' if pretrained else None)
        features = list(vgg.features.children())

        # Frontend: VGG16 layers 0-22
        self.frontend = nn.Sequential(*features[:23])

        # Backend: dilated convolutions for density map generation
        # Dilation captures crowd patterns at multiple scales
        self.backend = nn.Sequential(
            nn.Conv2d(512, 256, kernel_size=3, dilation=2, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 128, kernel_size=3, dilation=2, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 64, kernel_size=3, dilation=2, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 32, kernel_size=3, dilation=2, padding=2),
            nn.ReLU(inplace=True),
        )

        # Output: single channel density map
        self.output_layer = nn.Conv2d(32, 1, kernel_size=1)

        # Only initialize backend weights — frontend is already pretrained
        self._initialize_backend_weights()

    def forward(self, x):
        x = self.frontend(x)
        x = self.backend(x)
        x = self.output_layer(x)
        return x

    def _initialize_backend_weights(self):
        for m in self.backend.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
        nn.init.normal_(self.output_layer.weight, std=0.01)
        nn.init.constant_(self.output_layer.bias, 0)

    def count_people(self, density_map):
        """Sum density map to get total crowd count."""
        return density_map.sum().item()