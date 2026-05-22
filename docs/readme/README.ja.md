# ステーブルコイン市場における条件付き透明性

このリポジトリは、ステーブルコインの準備資産開示を対象とする公開データ・コード再現パッケージです。発行体開示の索引、研究者が確認した RQI/DII コーディング、日次市場パネル、イベント・ウィンドウ診断、頑健性出力、主張範囲の確認を含みます。

この公開版には、検査・再実行・拡張が可能な研究資料のみを収めています。データ、コード、文書、派生再現出力のみを含みます。

## 言語

| 言語 | README |
|---|---|
| English | [../../README.md](../../README.md) |
| 中文 | [README.zh-CN.md](README.zh-CN.md) |
| 日本語 | `README.ja.md` |
| Français | [README.fr.md](README.fr.md) |
| Русский | [README.ru.md](README.ru.md) |

## クイックスタート

```powershell
python -m pip install -r requirements.txt
python scripts\check_public_release.py
python scripts\run_public_replication.py --mode smoke
```

主な再現コマンド：

```powershell
python scripts\run_public_replication.py --mode analysis
python scripts\run_public_replication.py --mode all
```

第三者が発行する PDF、保存済みウェブページ、取得済み原資料は公開パッケージには再配布しません。公開データには、URL、アクセス日、ソース状態、イベント識別子、確認フラグを記録しています。結果は試行的診断として解釈してください。
