import calendar
import pandas as pd
import plotly.express as px
import streamlit as st

# 直接从标题开始，没有任何前置配置命令，彻底杜绝位置或版本报错
st.title("📈 跨境电商销售与日均销量分析看板 (1-10月)")
st.markdown(
    "请上传包含标准表头的订单数据文件（支持 `.csv` 或 `.xlsx` 格式）。"
)

# 文件上传组件
uploaded_file = st.file_uploader(
    "上传订单数据文件", type=["csv", "xlsx", "xls"]
)

if uploaded_file is not None:
  try:
    # 读取文件
    if uploaded_file.name.endswith(".csv"):
      df = pd.read_csv(uploaded_file, dtype=str)
    else:
      df = pd.read_excel(uploaded_file, dtype=str)

    # 必要的表头校验
    required_cols = ["Order Date", "Quantity", "产品SKU", "品牌", "产品名称"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
      st.error(
          f"上传的文件缺少以下核心表头字段: {', '.join(missing_cols)}，请检查数据源！"
      )
    else:
      # 数据清洗与类型转换
      df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
      df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)

      if "Total Cost" in df.columns:
        df["Total Cost"] = pd.to_numeric(
            df["Total Cost"], errors="coerce"
        ).fillna(0)

      # 提取年份和月份
      df["Year"] = df["Order Date"].dt.year
      df["Month"] = df["Order Date"].dt.month

      # 过滤 1-10 月的数据且排除年份为空的行
      df_filtered = df[
          (df["Month"] >= 1) & (df["Month"] <= 10) & (df["Year"].notna())
      ]

      if df_filtered.empty:
        st.warning(
            "未在数据中找到 1月到10月 之间的有效订单记录，请核对【Order"
            " Date】日期列格式。"
        )
      else:
        # 侧边栏筛选器
        st.sidebar.header("🔍 数据筛选")

        # 年份筛选
        available_years = sorted(
            df_filtered["Year"].dropna().astype(int).unique()
        )
        selected_year = st.sidebar.selectbox(
            "选择年份",
            available_years,
            index=len(available_years) - 1 if available_years else 0,
        )

        df_year = df_filtered[df_filtered["Year"] == selected_year].copy()

        # 品牌筛选
        if "品牌" in df_year.columns:
          brands = ["全部"] + sorted(
              df_year["品牌"].dropna().astype(str).unique().tolist()
          )
          selected_brand = st.sidebar.selectbox("品牌筛选", brands)
          if selected_brand != "全部":
            df_year = df_year[df_year["品牌"] == selected_brand]

        # 运营筛选
        if "运营" in df_year.columns:
          operators = ["全部"] + sorted(
              df_year["运营"].dropna().astype(str).unique().tolist()
          )
          selected_op = st.sidebar.selectbox("运营人员筛选", operators)
          if selected_op != "全部":
            df_year = df_year[df_year["运营"] == selected_op]

        if df_year.empty:
          st.warning("当前筛选条件下没有数据，请调整筛选选项。")
        else:
          # --- 核心计算：按月汇总销量及日均销量 ---
          monthly_summary = (
              df_year.groupby("Month")
              .agg(
                  Total_Qty=("Quantity", "sum"),
                  Total_Amount=(
                      "Total Cost"
                      if "Total Cost" in df_year.columns
                      else "Quantity",
                      "sum",
                  ),
                  Order_Count=("Order Date", "count"),
              )
              .reset_index()
          )

          # 计算每月天数
          days_in_month = {
              m: calendar.monthrange(int(selected_year), m)[1]
              for m in range(1, 11)
          }
          monthly_summary["Days_In_Month"] = monthly_summary["Month"].map(
              days_in_month
          )

          # 日均销量 = 当月总销量 / 当月天数
          monthly_summary["Daily_Avg_Qty"] = (
              monthly_summary["Total_Qty"] / monthly_summary["Days_In_Month"]
          )

          # 补齐 1-10 月中可能缺失的月份（填 0）
          all_months = pd.DataFrame({"Month": list(range(1, 11))})
          monthly_summary = pd.merge(
              all_months, monthly_summary, on="Month", how="left"
          ).fillna(
              {
                  "Total_Qty": 0,
                  "Total_Amount": 0,
                  "Order_Count": 0,
                  "Daily_Avg_Qty": 0,
              }
          )
          monthly_summary["Month_Str"] = (
              monthly_summary["Month"].astype(str) + "月"
          )
          monthly_summary = monthly_summary.sort_values("Month")

          # --- 顶部 KPI 指标看板 ---
          st.markdown(f"### 📊 {selected_year} 年 1-10月 核心经营总览")
          col1, col2, col3, col4 = st.columns(4)

          total_qty_sum = monthly_summary["Total_Qty"].sum()
          total_amt_sum = monthly_summary["Total_Amount"].sum()

          col1.metric("1-10月累计总销量", f"{total_qty_sum:,.0f} 件")
          if "Total Cost" in df.columns:
            col2.metric("1-10月累计总金额", f"${total_amt_sum:,.2f}")
          else:
            col3.metric("总订单行数", f"{monthly_summary['Order_Count'].sum():,}")
          col4.metric(
              "1-10月综合日均销量",
              f"{monthly_summary['Daily_Avg_Qty'].mean():,.1f} 件/天",
          )

          st.markdown("---")

          # --- 图表展示 ---
          st.subheader("📅 1-10月各月【日均销量】趋势看板")

          fig = px.bar(
              monthly_summary,
              x="Month_Str",
              y="Daily_Avg_Qty",
              text=monthly_summary["Daily_Avg_Qty"].round(1),
              labels={"Month_Str": "月份", "Daily_Avg_Qty": "日均销量 (件/天)"},
              title=f"{selected_year} 年 1-10月 各月日均销量走势",
              color="Daily_Avg_Qty",
              color_continuous_scale="Blues",
          )
          fig.update_traces(textposition="outside")
          fig.update_layout(
              xaxis_title="月份",
              yaxis_title="日均销量 (件/天)",
              template="plotly_white",
          )
          st.plotly_chart(fig, use_container_width=True)

          # 详细数据表格
          with st.expander("📋 查看各月详细销量与日均明细数据"):
            display_df = monthly_summary[
                [
                    "Month_Str",
                    "Total_Qty",
                    "Days_In_Month",
                    "Daily_Avg_Qty",
                    "Order_Count",
                ]
            ].copy()
            display_df.columns = [
                "月份",
                "当月总销量",
                "当月天数",
                "日均销量",
                "订单行数",
            ]
            display_df["日均销量"] = display_df["日均销量"].round(2)
            st.dataframe(display_df, use_container_width=True)

          # SKU 维度钻取
          st.subheader("🏆 产品 SKU 销量贡献排行 (Top 10)")
          sku_group = (
              df_year.groupby(
                  ["产品SKU", "产品名称", "品牌"]
                  if "产品名称" in df_year.columns
                  else ["产品SKU"]
              )
              .agg(
                  Total_Qty=("Quantity", "sum"),
                  Total_Amount=(
                      "Total Cost"
                      if "Total Cost" in df_year.columns
                      else "Quantity",
                      "sum",
                  ),
              )
              .reset_index()
              .sort_values(by="Total_Qty", ascending=False)
              .head(10)
          )
          st.dataframe(sku_group, use_container_width=True)

  except Exception as e:
    st.error(f"解析文件或渲染看板时发生错误: {e}")
else:
  st.info("👈 请在左侧上传你的订单数据文件（CSV / Excel）以生成看板。")
