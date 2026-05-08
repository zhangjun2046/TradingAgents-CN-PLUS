# PWA图标生成指南

## 方法一：使用在线工具（推荐）

访问 `http://localhost:3000/generate-icons.html` 使用内置的图标生成工具。

## 方法二：使用在线服务

1. 访问 https://realfavicongenerator.net/
2. 上传 `frontend/public/logo.svg`
3. 下载生成的图标包
4. 将以下文件放到 `frontend/public/` 目录：
   - `icon-192.png`
   - `icon-512.png`
   - `apple-touch-icon.png`

## 方法三：使用ImageMagick命令行

如果已安装 ImageMagick，可以使用以下命令：

```bash
# 进入 frontend/public 目录
cd frontend/public

# 生成 192x192 图标
magick convert logo.svg -resize 192x192 -background white -flatten icon-192.png

# 生成 512x512 图标
magick convert logo.svg -resize 512x512 -background white -flatten icon-512.png

# 生成 180x180 Apple图标
magick convert logo.svg -resize 180x180 -background white -flatten apple-touch-icon.png
```

## 方法四：使用Node.js脚本

创建临时脚本 `generate-pwa-icons.js`：

```javascript
const sharp = require('sharp');
const fs = require('fs');

const sizes = [
  { size: 192, name: 'icon-192.png' },
  { size: 512, name: 'icon-512.png' },
  { size: 180, name: 'apple-touch-icon.png' }
];

async function generateIcons() {
  const svgBuffer = fs.readFileSync('logo.svg');
  
  for (const { size, name } of sizes) {
    await sharp(svgBuffer)
      .resize(size, size, {
        fit: 'contain',
        background: { r: 255, g: 255, b: 255, alpha: 1 }
      })
      .png()
      .toFile(name);
    console.log(`✅ Generated ${name}`);
  }
}

generateIcons().catch(console.error);
```

运行：
```bash
npm install sharp
node generate-pwa-icons.js
```

## 所需文件清单

确保 `frontend/public/` 目录包含以下文件：

- ✅ `icon-192.png` - 192x192像素，用于Android等平台
- ✅ `icon-512.png` - 512x512像素，用于高分辨率设备
- ✅ `apple-touch-icon.png` - 180x180像素，用于iOS设备

## 验证

生成后，可以通过以下方式验证：

1. 启动开发服务器：`npm run dev`
2. 访问：
   - http://localhost:3000/icon-192.png
   - http://localhost:3000/icon-512.png
   - http://localhost:3000/apple-touch-icon.png
3. 确保图标正常显示

## 注意事项

- 图标应使用白色背景
- 确保SVG内容在图标中居中且大小适中
- 建议图标内容占据80%的空间，留20%边距
- PNG格式，真彩色（24位）+ Alpha通道

