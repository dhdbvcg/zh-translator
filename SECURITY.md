# 安全说明

## 已知的模型许可限制

本项目**代码**是 MIT 许可,但默认基座模型 **NLLB-200 是 CC-BY-NC-4.0(禁止商业用途)**。
详见 [MODEL_LICENSE.md](MODEL_LICENSE.md)。

## 密钥管理

本仓库**不包含任何密钥**,并已在 `.gitignore` 中显式排除:

```
apikey.md
*.key
*.pem
.env
.env.*
secrets.json
```

模型权重(`models/`,约 630 MB)同样不入库,由 `scripts/download_model.py` 本地下载。

## 本地服务安全

`zhtrans --serve` 默认监听 `127.0.0.1`,仅本机可访问。
它是一个**面向本地使用的工具**,没有内置认证与限流,因此:

- 不要直接暴露到公网;
- 需要多人访问时,请放在反向代理之后并自行加上鉴权;
- CORS 目前是开放的(`Access-Control-Allow-Origin: *`),
  若部署到内网且数据敏感,建议收紧该头。

## 报告问题

发现安全问题请通过 GitHub Issues 报告(请勿在公开 issue 中贴出密钥)。
