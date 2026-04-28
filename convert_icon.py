#!/usr/bin/env python3
"""
图标转换脚本
将 PNG 格式的 logo 转换为 ICO 格式，用于 Inno Setup 安装程序
"""

import os
import sys
from pathlib import Path

def convert_png_to_ico():
    """将PNG图标转换为ICO格式"""
    try:
        from PIL import Image, ImageDraw, ImageFilter
        print("正在转换图标文件...")
        
        # 输入和输出路径
        logo_png = Path("docs/logo.png")
        logo_ico = Path("docs/logo.ico")
        
        if not logo_png.exists():
            print(f"警告: 未找到 {logo_png}，将创建默认图标")
            create_default_icon(logo_ico)
            return
        
        # 打开PNG图片并检查尺寸
        with Image.open(logo_png) as img:
            print(f"原始图像尺寸: {img.size}, 模式: {img.mode}")
            
            # 转换为RGBA模式以确保透明度支持
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # 如果原图尺寸小于512x512，先放大到更高分辨率
            max_size = max(img.size)
            if max_size < 512:
                scale_factor = 512 / max_size
                new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                print(f"图像已放大到: {img.size}")
            
            # 应用锐化滤镜以提高清晰度
            img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=150, threshold=3))
            
            # 创建多个尺寸的高质量图标
            # 包含更多尺寸以适应不同显示需求
            sizes = [
                (16, 16),   # 小图标
                (20, 20),   # Windows 10 小图标
                (24, 24),   # 小工具栏图标
                (32, 32),   # 标准图标
                (40, 40),   # Windows 10 中等图标
                (48, 48),   # 大图标
                (64, 64),   # 超大图标
                (96, 96),   # Windows 10 大图标
                (128, 128), # 超大图标
                (256, 256), # 高清图标
                (512, 512)  # 超高清图标（如果支持）
            ]
            
            icons = []
            print("生成多尺寸图标:")
            
            for size in sizes:
                # 使用高质量重采样算法
                if img.size[0] >= size[0] and img.size[1] >= size[1]:
                    # 原图足够大，直接缩小
                    resized = img.resize(size, Image.Resampling.LANCZOS)
                else:
                    # 原图太小，使用最近邻算法避免模糊
                    resized = img.resize(size, Image.Resampling.NEAREST)
                
                # 对小尺寸图标进行额外的锐化处理
                if size[0] <= 48:
                    resized = resized.filter(ImageFilter.SHARPEN)
                
                icons.append(resized)
                print(f"  ✓ {size[0]}x{size[1]}")
            
            # 保存为高质量ICO文件
            print("保存ICO文件...")
            
            # 优先使用128x128单尺寸以获得更大的文件大小
            # 这解决了Pillow在多尺寸ICO上的兼容性问题
            icon_128 = None
            for i, size in enumerate(sizes):
                if size == (128, 128):
                    icon_128 = icons[i]
                    break
            
            if icon_128:
                # 使用128x128作为主图标（平衡质量和大小）
                icon_128.save(
                    logo_ico,
                    format='ICO',
                    sizes=[(128, 128)],
                    optimize=False,
                    quality=100
                )
                print(f"使用128x128单尺寸保存")
            else:
                # 回退到最大尺寸
                largest_icon = icons[-1]  # 最后一个是最大的
                largest_size = sizes[-1]
                largest_icon.save(
                    logo_ico,
                    format='ICO',
                    sizes=[largest_size],
                    optimize=False,
                    quality=100
                )
                print(f"使用{largest_size[0]}x{largest_size[1]}单尺寸保存")
        
        # 检查生成的ICO文件大小
        ico_size = logo_ico.stat().st_size
        print(f"图标转换完成: {logo_ico} (文件大小: {ico_size / 1024:.1f} KB)")
        
        if ico_size < 5000:  # 如果小于5KB可能质量不够
            print("⚠ 警告: ICO文件较小，可能需要检查图标质量")
        
        # 创建安装程序背景图片
        create_installer_images()
        
    except ImportError:
        print("警告: 未安装 Pillow 库，将创建默认图标")
        create_default_icon(Path("docs/logo.ico"))
    except Exception as e:
        print(f"图标转换失败: {e}")
        create_default_icon(Path("docs/logo.ico"))

def create_default_icon(ico_path):
    """创建高质量默认图标"""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        
        print("创建高质量默认图标...")
        
        # 创建高分辨率的基础图像
        base_size = 512
        img = Image.new('RGBA', (base_size, base_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 设计参数
        margin = base_size // 20  # 26px 边距
        border_width = base_size // 60  # 8px 边框
        
        # 创建渐变背景 - 从深蓝到浅蓝
        for y in range(base_size):
            progress = y / base_size
            # 使用更美观的渐变色彩
            r = int(52 + (100 - 52) * progress)   # 52 -> 100
            g = int(152 + (180 - 152) * progress) # 152 -> 180
            b = int(219 + (255 - 219) * progress) # 219 -> 255
            color = (r, g, b, 255)
            
            # 绘制水平渐变线
            draw.line([(margin, y), (base_size - margin, y)], fill=color)
        
        # 创建圆形遮罩
        mask = Image.new('L', (base_size, base_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        
        # 绘制圆形
        circle_margin = margin + border_width
        mask_draw.ellipse(
            [circle_margin, circle_margin, 
             base_size - circle_margin, base_size - circle_margin], 
            fill=255
        )
        
        # 应用圆形遮罩
        img.putalpha(mask)
        
        # 绘制边框
        draw.ellipse(
            [margin, margin, base_size - margin, base_size - margin], 
            outline=(25, 118, 185, 255), 
            width=border_width
        )
        
        # 绘制主文字 "M"
        try:
            # 尝试使用高质量系统字体
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Linux
            ]
            
            font = None
            font_size = base_size // 3  # 170px
            
            for font_path in font_paths:
                try:
                    if Path(font_path).exists():
                        font = ImageFont.truetype(font_path, font_size)
                        print(f"使用字体: {font_path}")
                        break
                except:
                    continue
            
            if font is None:
                # 使用默认字体
                font = ImageFont.load_default()
                
        except Exception as e:
            print(f"字体加载失败: {e}，使用默认字体")
            font = ImageFont.load_default()
        
        # 计算文字位置
        text = "M"
        
        try:
            # 新版本 Pillow 使用 textbbox
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            # 旧版本 Pillow 使用 textsize
            text_width, text_height = draw.textsize(text, font=font)
        
        x = (base_size - text_width) // 2
        y = (base_size - text_height) // 2 - font_size // 20  # 略微上移
        
        # 绘制文字阴影（增加立体感）
        shadow_offset = base_size // 100  # 5px 阴影偏移
        draw.text((x + shadow_offset, y + shadow_offset), text, 
                 fill=(0, 0, 0, 80), font=font)  # 半透明黑色阴影
        
        # 绘制主文字
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
        
        # 创建多个尺寸的高质量图标
        sizes = [
            (16, 16), (20, 20), (24, 24), (32, 32), (40, 40),
            (48, 48), (64, 64), (96, 96), (128, 128), (256, 256)
        ]
        
        icons = []
        print("生成多尺寸默认图标:")
        
        for size_tuple in sizes:
            # 使用高质量重采样
            resized = img.resize(size_tuple, Image.Resampling.LANCZOS)
            
            # 对小尺寸图标进行锐化处理
            if size_tuple[0] <= 32:
                resized = resized.filter(ImageFilter.SHARPEN)
            
            icons.append(resized)
            print(f"  ✓ {size_tuple[0]}x{size_tuple[1]}")
        
        # 保存高质量ICO文件
        icons[0].save(
            ico_path,
            format='ICO',
            sizes=[(icon.width, icon.height) for icon in icons],
            append_images=icons[1:],
            optimize=False,  # 不压缩以保持质量
            quality=100      # 最高质量
        )
        
        # 检查生成的文件大小
        ico_size = ico_path.stat().st_size
        print(f"高质量默认图标创建完成: {ico_path} (文件大小: {ico_size / 1024:.1f} KB)")
        
    except Exception as e:
        print(f"创建高质量默认图标失败: {e}")
        try:
            # 回退到最简单的ICO文件生成
            with open(ico_path, 'wb') as f:
                # 创建一个最简单的 16x16 ICO 文件头
                ico_header = (
                    b'\x00\x00\x01\x00\x01\x00'  # ICO header
                    b'\x10\x10\x00\x00\x01\x00\x20\x00'  # 16x16, 32-bit
                    b'\x00\x04\x00\x00\x16\x00\x00\x00'  # data size and offset
                )
                f.write(ico_header)
                # 写入简单的蓝色像素数据
                pixel_data = b'\x00\x80\xFF\xFF' * 256  # 16x16 蓝色像素
                f.write(pixel_data)
            print(f"创建了最简单的默认ICO文件: {ico_path}")
        except Exception as fallback_error:
            print(f"回退方案也失败: {fallback_error}")

def create_installer_images():
    """创建安装程序所需的高质量背景图片"""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        
        print("创建安装程序高质量背景图片...")
        
        # 创建安装向导背景图 (164x314)
        bg_width, bg_height = 164, 314
        bg_img = Image.new('RGB', (bg_width, bg_height), (52, 152, 219))
        draw = ImageDraw.Draw(bg_img)
        
        # 创建复杂的渐变效果
        for y in range(bg_height):
            # 使用非线性渐变创建更动人的效果
            progress = y / bg_height
            
            # S型曲线渐变，使过渡更平滑
            smooth_progress = progress * progress * (3 - 2 * progress)
            
            # 主色调渐变: 深蓝 -> 浅蓝 -> 白色
            if progress < 0.7:
                # 蓝色渐变部分
                factor = smooth_progress / 0.7
                r = int(52 + (100 - 52) * factor)
                g = int(152 + (180 - 152) * factor)
                b = int(219 + (255 - 219) * factor)
            else:
                # 向白色过渡
                factor = (smooth_progress - 0.7) / 0.3
                r = int(100 + (245 - 100) * factor)
                g = int(180 + (250 - 180) * factor)
                b = int(255)
            
            color = (r, g, b)
            draw.line([(0, y), (bg_width, y)], fill=color)
        
        # 添加微妙的光效
        for x in range(bg_width // 4):
            alpha = 30 - (x * 30 // (bg_width // 4))
            if alpha > 0:
                overlay = Image.new('RGBA', (bg_width, bg_height), (255, 255, 255, alpha))
                bg_img = Image.alpha_composite(bg_img.convert('RGBA'), overlay).convert('RGB')
        
        bg_img.save("docs/installer_bg.bmp", format='BMP')
        print("安装向导背景图创建完成: docs/installer_bg.bmp")
        
        # 创建高质量小图标 (55x55)
        icon_size = 55
        small_img = Image.new('RGB', (icon_size, icon_size), (255, 255, 255))
        
        # 检查是否存在原始logo文件
        logo_path = Path("docs/logo.png")
        if logo_path.exists():
            try:
                with Image.open(logo_path) as logo:
                    print(f"使用原始 logo: {logo_path} (尺寸: {logo.size})")
                    
                    # 计算缩放比例，保持高质量
                    target_size = icon_size - 10  # 留出5px的边距
                    scale = min(target_size / logo.width, target_size / logo.height)
                    
                    new_width = int(logo.width * scale)
                    new_height = int(logo.height * scale)
                    
                    # 使用高质量重采样
                    logo_resized = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 应用锐化滤镜
                    logo_resized = logo_resized.filter(ImageFilter.UnsharpMask(radius=0.5, percent=120, threshold=2))
                    
                    # 计算居中位置
                    x = (icon_size - new_width) // 2
                    y = (icon_size - new_height) // 2
                    
                    # 粘贴logo
                    if logo_resized.mode == 'RGBA':
                        small_img.paste(logo_resized, (x, y), logo_resized)
                    else:
                        small_img.paste(logo_resized, (x, y))
                    
                    print(f"原始logo已缩放到: {new_width}x{new_height}")
                    
            except Exception as logo_error:
                print(f"加载原始logo失败: {logo_error}，创建默认图标")
                create_default_small_icon(small_img, icon_size)
        else:
            print("未找到原姻logo文件，创建默认图标")
            create_default_small_icon(small_img, icon_size)
        
        small_img.save("docs/installer_icon.bmp", format='BMP')
        print("安装程序小图标创建完成: docs/installer_icon.bmp")
        
    except Exception as e:
        print(f"创建安装程序图片失败: {e}")

def create_default_small_icon(img, size):
    """为安装程序创建默认小图标"""
    try:
        from PIL import ImageDraw, ImageFont
        
        draw = ImageDraw.Draw(img)
        
        # 绘制圆形背景
        margin = 8
        circle_size = size - 2 * margin
        center_x = size // 2
        center_y = size // 2
        
        # 绘制渐变圆形
        for r in range(circle_size // 2, 0, -1):
            progress = r / (circle_size // 2)
            color_intensity = int(52 + (152 - 52) * (1 - progress))
            color = (color_intensity, 152, 219)
            
            draw.ellipse(
                [center_x - r, center_y - r, center_x + r, center_y + r],
                fill=color
            )
        
        # 绘制文字
        try:
            font_size = size // 3
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        text = "M"
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            text_width, text_height = draw.textsize(text, font=font)
        
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - 2
        
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        
    except Exception as e:
        print(f"创建默认小图标失败: {e}")

def check_license():
    """检查并创建许可证文件"""
    license_path = Path("LICENSE")
    if not license_path.exists():
        print("警告: 未找到 LICENSE 文件，将创建默认许可证")
        license_content = """MSST WebUI License

Copyright (c) 2024 SUC-DriverOld

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
        with open(license_path, 'w', encoding='utf-8') as f:
            f.write(license_content)
        print("默认许可证文件已创建")

def main():
    """主函数"""
    print("=== MSST WebUI 图标转换工具 ===")
    
    # 检查并创建必要的目录
    os.makedirs("docs", exist_ok=True)
    
    # 转换图标
    convert_png_to_ico()
    
    # 检查许可证
    check_license()
    
    print("图标转换完成！")

if __name__ == "__main__":
    main()