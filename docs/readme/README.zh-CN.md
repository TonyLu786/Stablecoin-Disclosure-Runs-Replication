# 稳定币市场中的条件透明度

本仓库是一个公开数据与代码复现包，用于复现一项关于稳定币储备披露的来源审计型研究。它包含发行人披露索引、研究者复核后的 RQI/DII 编码、日频市场面板、事件窗口诊断、稳健性输出和声明边界检查。

本公开版本只包含可检查、可复跑、可扩展的研究材料；仅包含数据、代码、文档与派生复现输出。

## 语言

| 语言 | README |
|---|---|
| English | [../../README.md](../../README.md) |
| 中文 | `README.zh-CN.md` |
| 日本語 | [README.ja.md](README.ja.md) |
| Français | [README.fr.md](README.fr.md) |
| Русский | [README.ru.md](README.ru.md) |

## 快速开始

```powershell
python -m pip install -r requirements.txt
python scripts\check_public_release.py
python scripts\run_public_replication.py --mode smoke
```

主要复现路径：

```powershell
python scripts\run_public_replication.py --mode analysis
python scripts\run_public_replication.py --mode all
```

原始第三方 PDF、网页保存件和抓取材料不随公开仓库分发；公开包记录来源 URL、访问日期、来源状态、事件标识和复核标记。所有结果均应理解为试点诊断，不构成投资、法律、监管或政策建议。
