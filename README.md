# NDPR MCDR Plugin

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![MCDR](https://img.shields.io/badge/MCDR-2.x+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-red.svg)

**NDPR 封禁系统 MCDR 插件**

[官网](https://ndpreforged.com) • [文档](#文档) • [QQ群](https://qm.qq.com/cgi-bin/qm/qr?k=232760327)

</div>

---

## 📖 简介

NDPR (NotDPR) 是一个强大的 Minecraft 服务器玩家封禁系统插件，通过云端封禁数据库实现跨服联防。支持正版服和离线服，可精准封禁玩家 ID、UUID、IP 地址和 IPv6 地址。

### 主要功能

- **多维封禁**：支持 ID、UUID、IPv4、IPv6 四种方式封禁
- **云端同步**：实时更新封禁数据库，跨服联防
- **智能检测**：玩家加入时自动检查封禁状态
- **日志分析**：自动解析服务器日志提取玩家信息
- **自动更新**：可配置自动更新封禁列表
- **自定义日志**：支持自定义日志处理格式

---

##  系统要求

| 要求 | 版本 |
|------|------|
| Python | 3.9+ |
| MCDR | 2.x 或更高版本 |
| 服务器 | Java 版 Minecraft 服务器 |

---

##  快速开始

### 安装

1. 下载插件文件：`ndpr.mcdr`
2. 将文件放入 MCDR 的 `plugins` 目录
3. 重启 MCDR 或使用 `!!MCDR plg load ndpr` 加载插件

### 配置

插件首次加载后会自动生成配置文件 `config.toml`：

```toml
# 服务器模式（必填）
onlinemode = true   # 正版服
# 或
onlinemode = false  # 离线服

# API 地址（通常无需修改）
api_url = "https://api.ndpreforged.com"

# Token（必填，需要启用封禁功能）
token = ""

# 日志文件路径
log_path = "server/logs/latest.log"

# 日志处理模式
logger_mode = "default"  # default 或 custom

# 自定义日志格式（logger_mode = "custom" 时生效）
logger_format = "<[%n%]%name%>%s%<%message%>"

# 封禁列表更新间隔（秒）
download_interval = 900
```

### 获取 Token

1. 启动插件，系统会自动获取 UUID
2. 复制获取到的 UUID
3. 前往 [官网](https://ndpreforged.com) 绑定邮箱
4. 系统自动发放 Token
5. 将 Token 填入配置文件
6. 重启插件

---

##  命令列表

| 命令 | 说明 |
|------|------|
| `!!ndpr` / `!!ndpr help` | 显示帮助信息 |
| `!!ndpr d` / `!!ndpr download` | 手动下载封禁数据库 |
| `!!ndpr ban <玩家名>` | 提交封禁审核 |
| `!!ndpr check <ID/IP/UUID>` | 检查封禁状态 |
| `!!ndpr reload` | 重载插件 |
| `!!ndpr cu` / `!!ndpr checkupdate` | 检查插件更新 |

### 命令示例

```bash
# 显示帮助
!!ndpr help

# 下载封禁数据库
!!ndpr download

# 提交封禁审核
!!ndpr ban Steve

# 检查玩家封禁状态
!!ndpr check Steve
!!ndpr check 192.168.1.1
!!ndpr check 123e4567-e89b-12d3-a456-426614174000

# 重载插件
!!ndpr reload

# 检查更新
!!ndpr checkupdate
```

---

##  配置详解

### 服务器模式 (onlinemode)

- `true`：正版服，使用 Mojang UUID 验证
- `false`：离线服，使用本地 UUID 生成

### 日志处理模式 (logger_mode)

#### default（默认模式）
自动解析标准 Minecraft 服务器日志，提取玩家信息。

#### custom（自定义模式）
使用自定义格式解析日志，适用于非标准服务器日志。

**格式说明：**

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `%ip%` | IP 地址 | `192.168.1.1` |
| `%uuid%` | UUID | `123e4567-e89b-12d3-a456-426614174000` |
| `%name%` | 玩家名 | `Steve` |
| `%message%` | 消息内容 | `Hello World` |
| `%n%` | 忽略该处内容 | - |
| `%s%` | 空格 | ` ` |

**示例：**
```toml
# 格式：<[头衔]>玩家名 <消息>
logger_format = "<[%n%]%name%>%s%<%message%>"
```

### 更新间隔 (download_interval)

封禁数据库自动更新间隔，单位：秒

- 默认：900 秒（15 分钟）
- 建议：根据服务器规模调整
- 设置为 `0`：禁用自动更新

---

## 安全性

### 数据保护

- 所有数据传输使用 HTTPS 加密
- UUID 用于身份识别，不包含敏感信息
- IP 地址仅用于封禁验证

### 隐私说明

- 不会收集玩家聊天记录
- 不会记录非封禁玩家信息
- 符合数据保护法规

---

## 故障排除

### 插件无法加载

**错误：** `请在ndpr配置文件里填写服务器类型(正版或离线)`

**解决：**
1. 编辑 `config.toml`
2. 设置 `onlinemode = true`（正版）或 `onlinemode = false`（离线）
3. 保存文件
4. 使用 `!!MCDR reload plugin ndpr` 重载插件

### Token 未配置

**错误：** `Token未配置请去官网获取`

**解决：**
1. 检查配置文件中 `token` 是否为空
2. 前往官网获取 Token
3. 填入配置文件并重载

### 日志文件不存在

**错误：** `日志文件不存在`

**解决：**
1. 检查 `log_path` 路径是否正确
2. 确认服务器日志文件存在
3. 路径相对于 MCDR 根目录

### 无法获取 UUID

**错误：** `API响应错误`

**解决：**
1. 检查网络连接
2. 确认 `api_url` 正确
3. 检查防火墙设置

---

##  贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

##  许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

##  联系方式

- **官网**：https://ndpreforged.com
- **QQ群**：232760327
- **GitHub**：https://github.com/NDPReforged/NDPR-MCDR

---

##  致谢

感谢所有为 NDPR 项目做出贡献的开发者和用户！

- MCDR 团队提供的优秀插件框架
- 所有测试用户的反馈和建议
- 社区成员的积极贡献

---

<div align="center">

**Made with ❤️ by NDPReforged Team**

[返回顶部](#ndpr-mcdr-plugin)

</div>
