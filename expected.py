# expected.py — 用原始 CSV 独立算出标准答案，作为 agent 的验收依据
import glob
import pandas as pd

files = sorted(glob.glob("../variance-qa-agent/data/budget_actual_2026-*.csv"))
source = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

fmt = "{:,.0f}".format  # 千分位格式，和 agent 的显示方式一致

# 1. 按部门汇总
print("== By department ==")
print(source.groupby("Department")["Budget"].sum().map(fmt))

# 2. 按类别汇总（全部门）
print("\n== By category ==")
print(source.groupby("Category")["Budget"].sum().map(fmt))

# 3. 部门 × 类别交叉汇总
print("\n== By department x category ==")
print(source.groupby(["Department", "Category"])["Budget"].sum().map(fmt))

# 4. 按月份汇总（用于验收月份筛选）
print("\n== By month ==")
print(source.groupby("Month")["Budget"].sum().map(fmt))

# 5. 测试用的特定组合
months = pd.to_datetime(source["Month"])
q1 = source[(months >= "2026-01-01") & (months <= "2026-03-01")]
print("\nJan to Mar 2026:", fmt(q1["Budget"].sum()))
mkt_feb = source[(source["Department"] == "Marketing") & (months == "2026-02-01")]
print("Marketing, Feb 2026:", fmt(mkt_feb["Budget"].sum()))
q4 = source[(months >= "2026-04-01") & (months <= "2026-06-01")]
print("Apr to Jun 2026:", fmt(q4["Budget"].sum()))
mar_on = source[months >= "2026-03-01"]
print("Mar 2026 onwards:", fmt(mar_on["Budget"].sum()))
tr_mar = source[(source["Category"] == "Travel") & (months == "2026-03-01")]
print("Travel, Mar 2026:", fmt(tr_mar["Budget"].sum()))

print("\nTotal:", fmt(source["Budget"].sum()))