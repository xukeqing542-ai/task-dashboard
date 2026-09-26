# 徐苛清｜商业分析与增长指标项目

**个人可复现作品。** 本项目以固定随机种子生成合成访客事件，从原始 CSV 经质量校验进入 SQLite，再产出日／周／月报与可视化。数据不来自扬腾创新或其他企业，也不代表真实业务成果。

## 快速运行

```bash
python -m pip install -r portfolio/requirements.txt
python portfolio/run_pipeline.py
```

如从 GitHub 下载本分支 ZIP，进入解压后的项目目录运行以上命令。脚本自行生成 `raw/events_synthetic.csv`，并生成 `output/` 下的 SQLite、CSV、HTML 和 `summary.json`。

## 已核验输出

| 项目 | 结果 |
|---|---:|
| 原始事件 | 6,203 行 |
| 质检后入库 | 6,202 行 |
| 重复事件拒收 | 1 行 |
| 指标天数 | 90 天 |
| 订单／GMV | 449 笔／人民币 51,622.05 元 |
| 周报／月报 | 13 期／3 期 |

口径：DAU 为当天不同用户数；转化率为订单数除以活跃用户日；最后一天不参与 D1 留存分母。渠道去重用户可能跨渠道，不能简单相加。项目内另有[需求与埋点字典](ANALYSIS_SPEC.md)、[英文分析简报](ENGLISH_BRIEF.md)、[运行代码](run_pipeline.py)。

**Excel 工作簿**另作附件提供，含日报输入、渠道对账、公式周汇总和图表。GitHub 分支目前提供可直接运行的 Python 管道与指标文档，不将其称为已上线的企业看板或真实运营实验。
