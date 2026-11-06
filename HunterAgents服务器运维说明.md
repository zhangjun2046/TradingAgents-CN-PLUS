# HunterAgents 服务器运维说明

正式入口：**https://hunteragents.cn:8443/**。H5 在同一主机名的 `/m/`。不要拆成 `h5.` 或 `admin.`。

浏览器里写 `https://` 却不写端口时走 443。安全组没有放行 80 和 443，所以地址必须带 `:8443`。`www` 证书没申请，不要用 `www.hunteragents.cn`。

公网 IP `118.144.76.8`。代码目录 `D:\TradingAgents-CN-PLUS`。Nginx 目录 `D:\nginx`。不做开机自启。

---

## 已经上线的写法

| 项 | 写法 |
|----|------|
| 产品名 | HunterAgents（带 s） |
| Logo | `icons/hunteragent-v4-3-ai-pill.svg`，页面用的是据此导出的 `frontend/public/logo.svg` 和图标。H5 Tab 图标不换 |
| 登录副标题 | 多智能体股票分析学习平台 |
| 版权年 / 版本 | 2026，用户可见版本 1.0 |
| 备案号 | `京ICP备2021035986号-4`，链接 `https://beian.miit.gov.cn/`。没有京公网安备号 |
| 联系邮箱 | `ocm@onecloudmall.com` |
| 短信签名 | `北京万商云猫智汇`。这是腾讯云审核名，不要改成 HunterAgents |
| 协议主体 | 继续写「本公司」 |
| 免责 | 学习、研究、不构成投资建议 |
| 上游 | 只在关于页致谢里出现，并写明本产品不是 TradingAgents-CN |
| 微信预览地址 | `frontend/index.html` 的 `og:url`、`twitter:url` 是 `https://hunteragents.cn:8443/`。聊天工具若按这行打开，进的是 PC 首页，不是某一份 `/s/...` 报告 |

---

## 正式地址

| 地址 | 内容 |
|------|------|
| `https://hunteragents.cn:8443/` | PC。分享页 `/s/{token}` 也在这里 |
| `https://hunteragents.cn:8443/m/` | H5，例如 `/m/#/pages/reports/list` |
| `https://hunteragents.cn:8443/api/` | Nginx 转到本机 `127.0.0.1:8000` |

`http://118.144.76.8:3000` 和 `:3100` 只在临时看开发页面时用。3000 是 PC，3100 是 H5，登录不互通。正式入口用 8443。

H5 点「查看报告」打开 `https://hunteragents.cn:8443/s/{token}?from=app`，返回去 `https://hunteragents.cn:8443/m/#/pages/reports/list`。`/m/` 的 Nginx 配置不要加会退回 PC 首页的 `try_files`。返回后若仍是 PC 的 404，先注销浏览器里该站点的 Service Worker，或用无痕窗口再试。

页面上复制的分享链接用当前网址。飞书等后端拼出来的链接用服务器 `.env` 的 `PUBLIC_APP_URL`。

---

## 关机或重启后怎么启动

MongoDB、Redis 是 Windows 服务，重启后一般会自己起来。Nginx 和 Python 要手动开。不要注册成开机服务。

先看端口，已经在监听就不要再启动一次。

```bat
netstat -ano | findstr ":8443"
netstat -ano | findstr ":8000"
tasklist | findstr nginx
```

### Nginx

正常是 **2** 个 `nginx.exe`。已经是 2 个就不要再 `start nginx`，否则会变成 4 个，8443 仍只有其中一个在听。

**后台启动（日常用这个）。** 窗口可以关。

```bat
cd /d D:\nginx
start nginx
netstat -ano | findstr ":8443"
```

应看到 `0.0.0.0:8443`，状态是 `LISTENING`，并且只剩 2 个 `nginx.exe`。

**前台启动。** 光标会停住。

```bat
cd /d D:\nginx
nginx.exe
```

直接关这个窗口不会干净停掉 Nginx。要停掉，或进程多于 2 个时，先清干净再后台启动：

```bat
cd /d D:\nginx
nginx.exe -s quit
taskkill /IM nginx.exe /F
start nginx
```

`nginx.exe -s quit` 如果提示找不到进程，直接执行 `taskkill`。旧进程留下的 `FIN_WAIT_2` 会自己消失。

改完 `nginx.conf` 必须先保存。已在跑时另开窗口执行 `nginx.exe -s reload`。成功时常常没有输出。

### Python

8000 已经在监听就不要再开一个。

**前台启动。** 窗口必须留着。关掉或按 `Ctrl+C`，登录和分析都会失败。

```bat
cd /d D:\TradingAgents-CN-PLUS
python -m app
```

**后台启动（日常用这个）。** 若已经有前台窗口，先在那个窗口按 `Ctrl+C`。

```bat
cd /d D:\TradingAgents-CN-PLUS
start "" venv\Scripts\pythonw.exe -m app
netstat -ano | findstr ":8000"
```

看到 8000 在监听后，窗口可以关。日志在 `D:\TradingAgents-CN-PLUS\logs`。要停掉：

```bat
netstat -ano | findstr ":8000"
taskkill /PID 最后一列的进程号 /F
```

重启后的日常顺序就是这两条后台命令：先 `start nginx`，再 `pythonw.exe -m app`。

### 临时用 IP 打开开发页面

后端 8000 必须已经在监听。命令要在服务器上执行。窗口要留着，关掉对应端口就没了。安全组要放行 3000 或 3100。

PC：`http://118.144.76.8:3000`

```bat
cd /d D:\TradingAgents-CN-PLUS\frontend
npm run dev
```

H5：`http://118.144.76.8:3100/m/`

```bat
cd /d D:\TradingAgents-CN-PLUS\mobile
npm run dev:h5
```

这两个开发服务的接口转到 `http://localhost:8000`，和 8443 共用同一个后端。只开它们不会更新 8443 上的正式页面。不用时关掉窗口；若不再需要从外网访问，安全组也关掉 3000 和 3100。

---

## 更新正式页面

PC 不要用 `npm run build`，类型检查会让构建停住。

```bat
cd /d D:\TradingAgents-CN-PLUS\frontend
npx vite build
cd /d D:\TradingAgents-CN-PLUS\mobile
npm run build:h5
```

- `frontend\dist` 的内容 → `D:\nginx\html\pc`
- `mobile\dist\build\h5` 的内容 → `D:\nginx\html\m`

H5 生产构建不要设置 `VITE_PUBLIC_APP_URL`。`mobile/.env.production` 保持 `VITE_API_BASE` 为空。

改的是 PC 页面时，覆盖 `D:\nginx\html\pc` 后，已经打开过网站的浏览器若仍看到旧页面或 `/m/` 变成 PC 的 404，注销一次该站点的 Service Worker。

---

## 服务器 .env

只改服务器上的 `.env`，不要提交 Git。同一项只留一行，后写的会盖掉前面的。

```ini
DEBUG=false
HOST=127.0.0.1
PORT=8000
PUBLIC_APP_URL=https://hunteragents.cn:8443
ALLOWED_ORIGINS=["https://hunteragents.cn:8443","http://118.144.76.8:3000","http://118.144.76.8:3100"]
ALLOWED_HOSTS=["hunteragents.cn","118.144.76.8","localhost","127.0.0.1"]
```

`PUBLIC_APP_URL` 不要末尾斜杠。`SMS_SIGN_NAME` 保持 `北京万商云猫智汇`。`DEBUG=false` 之后，`ALLOWED_HOSTS` 没写上的主机会让接口返回 400。改完要停掉再启动 Python。不再用 3000、3100 时，从 `ALLOWED_ORIGINS` 去掉那两个 IP 地址。

---

## 域名和证书

解析：`@` 和 `www` 的 A 记录都是 `118.144.76.8`。不要添加 `h5`、`admin`。本机开了代理时，`ping` 可能显示 `198.18.x.x`，用 `nslookup hunteragents.cn 223.5.5.5` 核对，结果应是 `118.144.76.8`。

证书只绑 `hunteragents.cn`，文件是：

```text
D:\nginx\conf\cert\hunteragents.cn.pem
D:\nginx\conf\cert\hunteragents.cn.key
```

`.key` 不要进 Git。免费证一般一年，换文件后执行 `nginx.exe -s reload`。通配符 `*.hunteragents.cn` 不能代替裸域名。

`D:\nginx\conf\nginx.conf` 的 `http { }` 里要有已保存的 `include conf.d/*.conf;`。站点文件是 `D:\nginx\conf\conf.d\hunteragent.conf`：

```nginx
server {
    listen 80 default_server;
    server_name _;
    return 301 https://hunteragents.cn:8443$request_uri;
}

server {
    listen 80;
    server_name hunteragents.cn www.hunteragents.cn;
    return 301 https://hunteragents.cn:8443$request_uri;
}

server {
    listen 8443 ssl;
    server_name hunteragents.cn;
    client_max_body_size 100m;

    ssl_certificate     D:/nginx/conf/cert/hunteragents.cn.pem;
    ssl_certificate_key D:/nginx/conf/cert/hunteragents.cn.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    root D:/nginx/html/pc;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location = /m {
        return 301 /m/;
    }

    location /m/ {
        alias D:/nginx/html/m/;
        index index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

不要给 `/m/` 再加 `try_files`。没有 www 证书，不要再写 `server_name www.hunteragents.cn` 的 8443 站点。80 现在外网进不来，用户直接打开带 8443 的地址。

改配置后：

```bat
cd /d D:\nginx
nginx.exe -t
nginx.exe -s reload
```
