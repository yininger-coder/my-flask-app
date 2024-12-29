from flask import Flask, request, render_template, send_file, redirect, url_for
import pandas as pd
import matplotlib.pyplot as plt
import os
import re
from io import BytesIO
import base64


app = Flask(__name__)

# 设置Matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体为SimHei（黑体）
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 指定CSV文件路径
FILE_PATH = r"C:\程序化\pycharm\rf_predict2.csv"  # 修改为你的文件路径


def process_header(header):
    """处理列名：去掉列名中的 0:00:00。"""
    return [col.replace("00:00:00", "").strip() for col in header]


def process_cell(value):
    """处理单元格数据：去掉 .csv、.SH 和 .SZ 后缀，并补零。"""
    value = str(value)  # 确保是字符串类型
    value = value.replace(".csv", "").replace(".SH", "").replace(".SZ", "")
    if re.match(r'^\d{1,6}$', value):  # 如果是1到6位数字，补零到6位
        value = value.zfill(6)
    return value


def process_table(FILE_PATH):
    """处理 CSV 文件：读取文件，处理列名和单元格数据，并保存处理后的数据。"""
    try:
        df = pd.read_csv(FILE_PATH)
        df.columns = process_header(df.columns)
        df = df.map(process_cell)
        output_path = os.path.splitext(FILE_PATH)[0] + "_processed.csv"
        df.to_csv(output_path, index=False)
        print(f"文件已处理并保存为: {output_path}")
        return output_path
    except Exception as e:
        print(f"处理文件 {FILE_PATH} 时出错: {e}")
        return None


def load_data(output_path):
    """加载处理后的数据。"""
    df = pd.read_csv(output_path)
    return df


def query_stock_rank(df, stock_code, n_days):
    """查询股票在最近N天的排名。"""
    try:
        # 将用户输入的股票代码转换为整数
        stock_code = int(stock_code)
    except ValueError:
        return None, "股票代码必须是六位数字"

    stock_row = df[df['new_predict'] == stock_code]
    if stock_row.empty:
        return None, "股票代码未找到"

    # 确保查询的天数不超过CSV文件中的列数
    max_days = len(df.columns) - 1  # 排除最后一列（new_predict）
    if n_days > max_days:
        return None, f"查询天数超过最大天数 {max_days}"

    recent_columns = df.columns[-n_days - 1:-1]  # 排除最后一列（new_predict）
    ranks = {}
    for column in recent_columns:
        sorted_values = df[column].sort_values(ascending=False).reset_index(drop=True)
        rank = sorted_values[sorted_values == stock_row[column].values[0]].index[0] + 1
        ranks[column] = rank
    return ranks, None  # 返回排名数据和 None（表示无错误）


def plot_rank_trend(ranks):
    """绘制排名变化趋势图并返回图像的 base64 编码。"""
    dates = list(ranks.keys())
    rank_values = list(ranks.values())
    plt.figure(figsize=(12, 6))
    plt.plot(dates, rank_values, marker='o', linestyle='-', color='b', markersize=8, label="排名")

    # 在每个数据点上添加排名信息
    for date, rank in ranks.items():
        plt.annotate(
            f"{rank}",  # 显示的文本
            (date, rank),  # 文本的位置
            textcoords="offset points",  # 文本位置的偏移方式
            xytext=(0, 10),  # 文本位置的偏移量
            ha='center',  # 水平对齐方式
            fontsize=10,  # 字体大小
            color='red'  # 字体颜色
        )

    plt.title("股票排名变化趋势", fontsize=16)
    plt.xlabel("日期", fontsize=12)
    plt.ylabel("排名", fontsize=12)
    plt.gca().invert_yaxis()  # 排名越靠前越好，因此Y轴反转
    plt.grid(True)
    plt.xticks(rotation=45)  # 旋转日期标签，避免重叠
    plt.legend()  # 显示图例
    plt.tight_layout()

    # 将图像保存为 base64 编码
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
    plt.close()
    return img_base64


def generate_rank_text(ranks):
    """生成排名信息的文字内容。"""
    text = "日期\t排名\n"
    for date, rank in ranks.items():
        text += f"{date}\t{rank}\n"
    return text


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # 获取用户输入
        stock_code = request.form.get("stock_code")
        n_days = int(request.form.get("n_days"))

        # 检查股票代码是否为六位数字
        if not (stock_code.isdigit() and len(stock_code) == 6):
            return render_template("index.html", error_message="股票代码必须是六位数字", max_days=None)

        # 处理文件并加载数据
        processed_file_path = process_table(FILE_PATH)
        if not processed_file_path:
            return "文件处理失败，请检查文件路径。"
        df = load_data(processed_file_path)

        # 查询排名
        result, error_message = query_stock_rank(df, stock_code, n_days)
        if error_message:
            return render_template("index.html", error_message=error_message, max_days=len(df.columns) - 1)

        # 绘制趋势图
        img_base64 = plot_rank_trend(result)

        # 生成排名信息的文字内容
        rank_text = generate_rank_text(result)

        # 跳转到 result.html 并传递数据
        return render_template("result.html", stock_code=stock_code, img_base64=img_base64, rank_text=rank_text)

    # 如果是 GET 请求，显示首页
    return render_template("index.html", max_days=None)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)