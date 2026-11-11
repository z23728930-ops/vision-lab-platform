import torch
import torch.nn as nn
import torchvision.transforms.functional as F


# --- 1. UNet 模型定义 (自定义实现，从头开始训练) ---

# 新增：Channel Attention Module
class ChannelAttentionModule(nn.Module):
    def __init__(self, channel, reduction=16):
        super(ChannelAttentionModule, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)

        self.fc = nn.Sequential(
            nn.Conv2d(channel, channel // reduction, 1, bias=False),
            nn.ReLU(),
            nn.Conv2d(channel // reduction, channel, 1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        out = avg_out + max_out
        return self.sigmoid(out)

# 新增：Spatial Attention Module
class SpatialAttentionModule(nn.Module):
    def __init__(self, kernel_size=7):
        super(SpatialAttentionModule, self).__init__()
        self.conv1 = nn.Conv2d(2, 1, kernel_size, padding=kernel_size // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        x_cat = torch.cat([avg_out, max_out], dim=1)
        out = self.conv1(x_cat)
        return self.sigmoid(out)

# 新增：CBAM (Convolutional Block Attention Module)
class CBAM(nn.Module):
    def __init__(self, channel, reduction=16, kernel_size=7):
        super(CBAM, self).__init__()
        self.channel_attention = ChannelAttentionModule(channel, reduction)
        self.spatial_attention = SpatialAttentionModule(kernel_size)

    def forward(self, x):
        out = x * self.channel_attention(x)
        out = out * self.spatial_attention(out)
        return out

# DoubleConv 保持不变
class DoubleConv(nn.Module):
    """(convolution => [BN] => ReLU) * 2"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)

# UNet 类修改：在每个 DoubleConv 之后添加 CBAM
class UNet(nn.Module):
    # --- 修改：处理可变默认参数 ---
    def __init__(self, in_channels=3, out_channels=1, features=None):
        super().__init__()
        if features is None:
            features = [64, 128, 256, 512]
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # Encoder (Downsampling Path)
        self.conv_down1 = DoubleConv(in_channels, features[0])
        self.cbam1 = CBAM(features[0]) # 添加CBAM
        self.conv_down2 = DoubleConv(features[0], features[1])
        self.cbam2 = CBAM(features[1]) # 添加CBAM
        self.conv_down3 = DoubleConv(features[1], features[2])
        self.cbam3 = CBAM(features[2]) # 添加CBAM
        self.conv_down4 = DoubleConv(features[2], features[3])
        self.cbam4 = CBAM(features[3]) # 添加CBAM

        # Bottleneck
        self.bottleneck = DoubleConv(features[3], features[3] * 2)
        self.cbam_bottleneck = CBAM(features[3] * 2) # 添加CBAM到瓶颈层

        # Decoder (Upsampling Path)
        self.up_conv1 = nn.ConvTranspose2d(features[3] * 2, features[3], kernel_size=2, stride=2)
        self.conv_up1 = DoubleConv(features[3] * 2, features[3])
        self.cbam_up1 = CBAM(features[3]) # 添加CBAM

        self.up_conv2 = nn.ConvTranspose2d(features[3], features[2], kernel_size=2, stride=2)
        self.conv_up2 = DoubleConv(features[2] * 2, features[2])
        self.cbam_up2 = CBAM(features[2]) # 添加CBAM

        self.up_conv3 = nn.ConvTranspose2d(features[2], features[1], kernel_size=2, stride=2)
        self.conv_up3 = DoubleConv(features[1] * 2, features[1])
        self.cbam_up3 = CBAM(features[1]) # 添加CBAM

        self.up_conv4 = nn.ConvTranspose2d(features[1], features[0], kernel_size=2, stride=2)
        self.conv_up4 = DoubleConv(features[0] * 2, features[0])
        self.cbam_up4 = CBAM(features[0]) # 添加CBAM

        # Final 1x1 convolution to get desired output channels
        self.final_conv = nn.Conv2d(features[0], out_channels, kernel_size=1)

    def forward(self, x):
        # Encoder
        conv1 = self.conv_down1(x)
        conv1_att = self.cbam1(conv1) # 应用CBAM
        pool1 = self.pool(conv1_att)

        conv2 = self.conv_down2(pool1)
        conv2_att = self.cbam2(conv2) # 应用CBAM
        pool2 = self.pool(conv2_att)

        conv3 = self.conv_down3(pool2)
        conv3_att = self.cbam3(conv3) # 应用CBAM
        pool3 = self.pool(conv3_att)

        conv4 = self.conv_down4(pool3)
        conv4_att = self.cbam4(conv4) # 应用CBAM
        pool4 = self.pool(conv4_att)

        # Bottleneck
        bottleneck = self.bottleneck(pool4)
        bottleneck_att = self.cbam_bottleneck(bottleneck) # 应用CBAM

        # Decoder
        up4 = self.up_conv1(bottleneck_att) # 从带注意力的瓶颈层上采样
        # --- 修改：变量名改为小写 ---
        diff_y = conv4_att.size()[2] - up4.size()[2]
        diff_x = conv4_att.size()[3] - up4.size()[3]
        up4 = F.pad(up4, [diff_x // 2, diff_x - diff_x // 2, # <-- 修改：使用 F.pad
                           diff_y // 2, diff_y - diff_y // 2])
        up4 = torch.cat([conv4_att, up4], dim=1) # 拼接带注意力的skip连接
        up4 = self.conv_up1(up4)
        up4_att = self.cbam_up1(up4) # 应用CBAM

        up3 = self.up_conv2(up4_att)
        # --- 修改：变量名改为小写 ---
        diff_y = conv3_att.size()[2] - up3.size()[2]
        diff_x = conv3_att.size()[3] - up3.size()[3]
        up3 = F.pad(up3, [diff_x // 2, diff_x - diff_x // 2, # <-- 修改：使用 F.pad
                           diff_y // 2, diff_y - diff_y // 2])
        up3 = torch.cat([conv3_att, up3], dim=1)
        up3 = self.conv_up2(up3)
        up3_att = self.cbam_up2(up3) # 应用CBAM

        up2 = self.up_conv3(up3_att)
        # --- 修改：变量名改为小写 ---
        diff_y = conv2_att.size()[2] - up2.size()[2]
        diff_x = conv2_att.size()[3] - up2.size()[3]
        up2 = F.pad(up2, [diff_x // 2, diff_x - diff_x // 2, # <-- 修改：使用 F.pad
                           diff_y // 2, diff_y - diff_y // 2])
        up2 = torch.cat([conv2_att, up2], dim=1)
        up2 = self.conv_up3(up2)
        up2_att = self.cbam_up3(up2) # 应用CBAM

        up1 = self.up_conv4(up2_att)
        # --- 修改：变量名改为小写 ---
        diff_y = conv1_att.size()[2] - up1.size()[2]
        diff_x = conv1_att.size()[3] - up1.size()[3]
        up1 = F.pad(up1, [diff_x // 2, diff_x - diff_x // 2, # <-- 修改：使用 F.pad
                           diff_y // 2, diff_y - diff_y // 2])
        up1 = torch.cat([conv1_att, up1], dim=1)
        up1 = self.conv_up4(up1)
        up1_att = self.cbam_up4(up1) # 应用CBAM

        return self.final_conv(up1_att) # 最终卷积也接收带注意力的特征