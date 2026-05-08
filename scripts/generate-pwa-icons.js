#!/usr/bin/env node

/**
 * PWA图标生成脚本
 * 从 logo.svg 生成多尺寸PNG图标
 * 
 * 使用方法：
 * 1. 安装依赖：npm install sharp (如果未安装)
 * 2. 运行脚本：node scripts/generate-pwa-icons.js
 */

const fs = require('fs');
const path = require('path');

console.log('🎨 PWA图标生成脚本');
console.log('='.repeat(50));

// 检查是否安装了sharp
let sharp;
try {
  sharp = require('sharp');
  console.log('✅ sharp 模块已加载');
} catch (error) {
  console.log('❌ 未找到 sharp 模块');
  console.log('📦 正在尝试安装 sharp...');
  const { execSync } = require('child_process');
  try {
    execSync('npm install sharp --no-save', { stdio: 'inherit' });
    sharp = require('sharp');
    console.log('✅ sharp 安装成功');
  } catch (installError) {
    console.error('❌ 无法安装 sharp，请手动安装：npm install sharp');
    console.log('\n📝 备选方案：');
    console.log('1. 访问 http://localhost:3000/generate-icons.html 使用在线工具');
    console.log('2. 查看 frontend/public/ICON_GENERATION_GUIDE.md 获取更多方法');
    process.exit(1);
  }
}

const publicDir = path.join(__dirname, '../frontend/public');
const logoPath = path.join(publicDir, 'logo.svg');

// 检查logo.svg是否存在
if (!fs.existsSync(logoPath)) {
  console.error('❌ 未找到 logo.svg 文件:', logoPath);
  process.exit(1);
}

console.log('📂 工作目录:', publicDir);
console.log('🖼️  源文件:', logoPath);
console.log('');

// 定义需要生成的图标尺寸
const iconSizes = [
  { size: 192, name: 'icon-192.png', description: '192x192 标准图标' },
  { size: 512, name: 'icon-512.png', description: '512x512 高清图标' },
  { size: 180, name: 'apple-touch-icon.png', description: '180x180 Apple图标' }
];

async function generateIcons() {
  try {
    const svgBuffer = fs.readFileSync(logoPath);
    
    console.log('🚀 开始生成图标...\n');
    
    for (const { size, name, description } of iconSizes) {
      const outputPath = path.join(publicDir, name);
      
      await sharp(svgBuffer)
        .resize(size, size, {
          fit: 'contain',
          background: { r: 255, g: 255, b: 255, alpha: 1 }
        })
        .png()
        .toFile(outputPath);
      
      const stats = fs.statSync(outputPath);
      const fileSizeKB = (stats.size / 1024).toFixed(2);
      
      console.log(`✅ ${description}`);
      console.log(`   文件: ${name}`);
      console.log(`   大小: ${fileSizeKB} KB`);
      console.log('');
    }
    
    console.log('='.repeat(50));
    console.log('🎉 所有图标生成完成！');
    console.log('');
    console.log('📋 生成的文件：');
    iconSizes.forEach(({ name }) => {
      console.log(`   ✓ frontend/public/${name}`);
    });
    console.log('');
    console.log('💡 下一步：');
    console.log('   1. 启动开发服务器验证图标：npm run dev');
    console.log('   2. 访问 http://localhost:3000/icon-192.png 查看效果');
    console.log('   3. 检查 PWA manifest 配置是否正确');
    
  } catch (error) {
    console.error('❌ 生成图标时出错:', error.message);
    console.error(error);
    process.exit(1);
  }
}

// 执行生成
generateIcons();

