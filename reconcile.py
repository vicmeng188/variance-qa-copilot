# reconcile.py — 对账：Power Query 合并结果 vs 6 个原始 CSV
# 原则：Power Query 负责合并，Python 负责查账，两边独立算出同样的数才算过关
import glob
import pandas as pd

# 1. 读原始数据：找到 6 个月度 CSV，逐个读进来再上下拼接
#    文件名限定为 budget_actual_2026-*.csv，防止别的文件混进来
files = sorted(glob.glob("../variance-qa-agent/data/budget_actual_2026-*.csv"))
assert len(files) == 6, f"应找到 6 个 CSV，实际找到 {len(files)} 个"
source = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

# 2. 读合并结果：BudgetActual.xlsx 里名为 data 的工作表
merged = pd.read_excel("BudgetActual.xlsx", sheet_name="data")

# 统一 Month 类型：CSV 读进来是文本，Excel 读进来是日期，都转成日期才能比较
source["Month"] = pd.to_datetime(source["Month"])
merged["Month"] = pd.to_datetime(merged["Month"])

# 3. 核对①：总行数相等（抓丢行，或其他文件的表头混进来）
assert len(source) == len(merged), f"行数不符：原始 {len(source)}，合并 {len(merged)}"

# 4. 核对②：每个月的行数相等（抓某个文件被漏读或读了两次）
src_by_month = source.groupby("Month").size()
mrg_by_month = merged.groupby("Month").size()
assert src_by_month.equals(mrg_by_month), f"每月行数不符：\n原始：\n{src_by_month}\n合并：\n{mrg_by_month}"

# 5. 核对③④：Budget、Actual 总和分别相等（抓金额被改动，比如被四舍五入）
for col in ["Budget", "Actual"]:
    assert source[col].sum() == merged[col].sum(), f"{col} 总和不符：原始 {source[col].sum()}，合并 {merged[col].sum()}"

# 全部通过才会走到这里；任何一项不符，上面的 assert 会直接报错并说明哪里不对
print(f"✅ 对账通过：{len(merged)} 行，6 个月每月行数一致")
print(f"   Budget 合计 {merged['Budget'].sum():,.0f}，Actual 合计 {merged['Actual'].sum():,.0f}")