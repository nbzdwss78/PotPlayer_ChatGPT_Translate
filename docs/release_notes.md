# 📢 PotPlayer ChatGPT Translate v1.9.4

## 📦 下载地址 / Download

| 渠道 (Channel) | 下载链接 (Download Link) |
| --- | --- |
| **GitHub (Global)** | [👉 Download Latest Installer (v1.9.4)](https://github.com/Felix3322/PotPlayer_ChatGPT_Translate/releases/latest) |
| **Gitee (China)** | [🚀 国内镜像快速下载](https://gitee.com/felix3322/PotPlayer_ChatGPT_Translate/raw/master/releases/latest/installer.exe) |

---

## 🔧 更新内容 / Update Highlights

*   **[修复] 上下文翻译稳定性**：将旧的 token/字数预算上下文彻底替换为“最近字幕条数”上下文，默认发送最近 3 条字幕，并使用新的 `gpt_context_subtitle_count` 配置名避免旧版本配置冲突。
*   **[优化] 提示词边界**：使用 `<CONTEXT>` / `<CURRENT>` 明确分离上下文与当前字幕，减少请求耗时和偶发输出原文的问题（issue #92）。
*   **[发布] 多安装包构建**：同时生成 Python 和原生 C++ 安装包，并发布为最新 GitHub Release。

---

# 📢 PotPlayer ChatGPT Translate v1.9.2-release2

## 📦 下载地址 / Download

| 渠道 (Channel) | 下载链接 (Download Link) |
| --- | --- |
| **GitHub (Global)** | [👉 Download Latest Installer (v1.9.2-release2)](https://github.com/Felix3322/PotPlayer_ChatGPT_Translate/releases/latest) |
| **Gitee (China)** | [🚀 国内镜像快速下载](https://gitee.com/felix3322/PotPlayer_ChatGPT_Translate/raw/master/releases/latest/installer.exe) |

---

## 🔧 更新内容 / Update Highlights

*   **[重构] 安装器改为原生 C++ 实现**：将原先的 Python / PyQt 安装器迁移为单文件原生 Win32 C++ 版本，同时保留向导、自动探测、API 校验、预配置注入、注册表与卸载脚本等既有功能。
*   **[发布] 基于当前标签生成补充发行版**：保持基础 tag 为 **v1.9.2**，本次补充发行版后缀为 **-release2**，并重新生成最新 installer 二进制。

---

# 📢 PotPlayer ChatGPT Translate v1.9.2

## 📦 下载地址 / Download

| 渠道 (Channel) | 下载链接 (Download Link) |
| --- | --- |
| **GitHub (Global)** | [👉 Download Latest Installer (v1.9.2)](https://github.com/Felix3322/PotPlayer_ChatGPT_Translate/releases/latest) |
| **Gitee (China)** | [🚀 国内镜像快速下载](https://gitee.com/felix3322/PotPlayer_ChatGPT_Translate/raw/master/releases/latest/installer.exe) |

---

## 🔧 更新内容 / Update Highlights

*   **[修复] 无上下文脚本重复函数定义**：删除 `SubtitleTranslate - ChatGPT - Without Context.as` 末尾重复的 `FormatFailureTranslation`、`OnInitialize` 和 `OnFinalize`，修复播放视频/音频时弹出 AngelScript 报错窗口的问题（issue #100）。
*   **[构建] 重新生成安装包**：同步更新插件与安装器版本号到 **v1.9.2**，并重建 installer 二进制。

---

# 📢 PotPlayer ChatGPT Translate v1.9.0

## 📦 下载地址 / Download

| 渠道 (Channel) | 下载链接 (Download Link) |
| --- | --- |
| **GitHub (Global)** | [👉 Download Latest Installer (v1.9.0)](https://github.com/Felix3322/PotPlayer_ChatGPT_Translate/releases/latest) |
| **Gitee (China)** | [🚀 国内镜像快速下载](https://gitee.com/felix3322/PotPlayer_ChatGPT_Translate/raw/master/releases/latest/installer.exe) |

---

## 🔧 更新内容 / Update Highlights

**本次更新带来了架构级的稳定性提升和对小模型的深度优化：**

*   **[重构] 统一重试循环 (Unified Retry Loop)**：彻底重构了核心翻译逻辑，现在网络错误、API 报错和幻觉检测共享同一个重试计数器。这意味着如果网络偶尔超时，或者模型偶尔产生幻觉，脚本都能智能地利用剩余的重试机会自动恢复，再也不会因为单一类型的失败而卡死。
*   **[新增] 反幻觉机制 (Anti-Hallucination)**：新增了专门针对模型“幻觉”的检测功能。如果模型输出了长度异常（超过原文 5 倍）的内容，插件会将其视为失败并自动重试。此功能可在安装时选择开启或关闭。
*   **[新增] 小模型优化模式 (Small Model Mode)**：专为 `gpt-4o-mini`, `gemini-flash` 等轻量级模型设计。开启后，插件会严格分离 System Prompt（指令/上下文）和 User Prompt（仅原文），或者将指令移出 User Prompt，防止小模型将翻译指令误认为是需要翻译的文本，大幅提升小模型的指令遵循能力。
*   **[优化] 上下文缓存命中率 (Cache Hit Rate)**：针对支持 Context Caching 的模型（如 DeepSeek, OpenAI），优化了 Prompt 结构，确保 System Prompt 前缀更加稳定，从而显著提高缓存命中率，降低 API 成本并提升速度。
*   **[修复] 默认配置与安装逻辑**：
    *   将上下文缓存（Context Cache）默认设置为 **关闭**，以避免在不支持非标准端点的 API 上造成卡顿。
    *   修复了安装包预设配置在首次运行时可能未被正确加载的问题，现在即使用户未手动修改设置，也能正确使用安装时的选项。

---

## 📸 预览 / Screenshots

<p align="center">
  <img src="https://github.com/user-attachments/assets/d21a23f8-d580-400d-8e94-efc618b9c541" width="90%" alt="Banner" />
  <br><br>
  <img src="https://github.com/user-attachments/assets/ed644de9-f878-4978-bb54-5f1be48ad7d0" width="200" alt="Settings" />
</p>

---

# 📢 PotPlayer ChatGPT Translate v1.8

## 📦 下载地址 / Download

| 渠道 (Channel) | 下载链接 (Download Link) |
| --- | --- |
| **GitHub (Global)** | [👉 Download Latest Installer (v1.8)](https://github.com/Felix3322/PotPlayer_ChatGPT_Translate/releases/latest) |
| **Gitee (China)** | [🚀 国内镜像快速下载](https://gitee.com/felix3322/PotPlayer_ChatGPT_Translate/raw/master/releases/latest/installer.exe) |

---

## 🔧 更新内容 / Update Highlights

**本次更新主要集中在核心稳定性和字符处理的修复上，强烈建议所有用户升级：**

* **[重要修复]** **修复 JSON 转义失效问题**：修复了一个导致特殊字符（如引号、反斜杠、换行符）无法正确转义的严重 bug，大幅提升了复杂字幕内容的翻译稳定性。
* **[重要修复]** **修复 CJK 字符截断问题**：优化了上下文“智能修剪”逻辑，现在能正确处理 UTF-8 多字节字符（如中文、韩文），防止因字符被切断而导致的乱码或 API 报错。
* **[优化]** **增强 JSON 兼容性**：新增对退格符 (`\b`) 和换页符 (`\f`) 的转义支持，符合更严格的 JSON 规范。
* **[优化]** **重试逻辑安全网**：为网络重试机制添加了最大尝试次数限制，防止在网络不可用时陷入无限循环。

---

## 🛠 核心改进详情 / Technical Improvements

针对开发者与高级用户，本次更新在底层逻辑上做了以下调整：

> **AngelScript 修复: String Replace & Slicing**
> 修正了 `string.replace` 返回值未被重新赋值的低级错误；重写了 `Smart Trim` 算法，在截取字符串时会自动检测 UTF-8 边界，避免产生无效字节序列。

> **鲁棒性增强: Robustness**
> `ExecuteWithRetry` 函数现在拥有硬性的循环上限（10次），即使在极端的网络配置或错误状态下也能保证主线程不会卡死。

---

## 📸 预览 / Screenshots

<p align="center">
  <img src="https://github.com/user-attachments/assets/d21a23f8-d580-400d-8e94-efc618b9c541" width="90%" alt="Banner" />
  <br><br>
  <img src="https://github.com/user-attachments/assets/ed644de9-f878-4978-bb54-5f1be48ad7d0" width="200" alt="Settings" />
</p>

---

## ℹ️ 其他说明 / Additional Notes

* 💻 **运行环境**：建议在 **Windows 10 / 11** 系统下配合最新版 PotPlayer 运行。
* ⚠️ **升级提示**：由于修复了核心脚本逻辑，**请务必使用安装包重新安装**，或手动覆盖 `SubtitleTranslate - ChatGPT.as` 和 `SubtitleTranslate - ChatGPT - Without Context.as` 两个文件。
* 🐞 **问题反馈**：如遇安装或使用问题，请通过 [GitHub Issues](https://github.com/Felix3322/PotPlayer_ChatGPT_Translate/issues) 提交反馈。
