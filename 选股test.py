# pip install akshare 如果没有安装的话，要install一下
from signal import signal

import pandas as pd
import numpy as np
import akshare as ak
import time


def getStockInfo():
    df = ak.stock_zh_a_spot_em()
    # 上证
    sh_stock = df[
        df["代码"].astype(str).str.startswith("6").copy()
    ]
    sh_stock["代码"] = "sh" + sh_stock["代码"].astype(str)

    # 深证+创业板
    sz_stock = df[
        df["代码"].astype(str).str.startswith(("0", "3")).copy()
    ]
    sz_stock["代码"] = "sz" + sz_stock["代码"].astype(str)

    res = pd.concat([sh_stock, sz_stock])
    return res

def processSuperTrendSignal(df, period=10, multiplier=3):
    # 计算ATR
    df["TR"] = abs(df["high"] - df["close"].shift(1))
    atr_list = []
    for i in range(len(df)):
        if i < period - 1:
            atr_list.append(float("nan"))
        else:
            tr_slice = df["TR"].iloc[(i - period + 1):(i + 1)]
            atr = tr_slice.mean()
            atr_list.append(atr)
    df["ATR"] = atr_list

    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 计算supertrend的base和上下界
    df["base"] = (df["high"] + df["low"]) / 2
    df["upper_bound"] = df["base"] + multiplier * df["ATR"]
    df["lower_bound"] = df["base"] - multiplier * df["ATR"]
    conditions = [
        (df["close"] > df["upper_bound"]),
        (df["close"] < df["lower_bound"])
    ]

    # 处理信号
    choices = ["buy", "sell"]
    df["signal"] = pd.Series(np.select(conditions, choices, default="hold"), index=df.index)

    return df

def getStockData(code, period='30', adjust='hfq'):
    df = ak.stock_zh_a_minute(symbol=code, period=period, adjust=adjust)
    return df


if __name__ == "__main__":
    # 定义参数
    atr_multiplier = 3
    atr_period = 10
    his_period = '30' # 这里定义的是分时图的时间周期，'30'代表30分钟k线
    adjust = 'qfq' # 赋权方式，前复权是'qfq',默认是'qfq'后复权
    signal_period = 8 # 信号检测周期，默认8个时间片

    # 获取上市股票数据
    all_stock_data = getStockInfo()

    # 根据基本面数据进行初筛
    filtered_df = all_stock_data[
        (all_stock_data['量比'] > 1)
        & (all_stock_data['换手率'] > 5)
        # & (all_stock_data['总市值'] > 5000000000)
        & (all_stock_data['市盈率-动态'] > 0)
    ]
    stock_code_list = filtered_df["代码"].values
    print(stock_code_list)

    # 初始化循环配置
    result_list = []
    count = 0

    # 处理数据
    for stock_code in stock_code_list:
        try:
            df = getStockData(stock_code, period=his_period, adjust=adjust)

            result_df = processSuperTrendSignal(df, atr_period, atr_multiplier)
            result_df = result_df.sort_index(ascending=False)
            print(result_df.head(signal_period))

            signal_head = result_df["signal"].head(signal_period).tolist()
            print(signal_head)

            if "buy" in signal_head:
                result_list.append(stock_code)
                print(f"处理{stock_code}的时候发现了趋势信号，赶紧买入！")
            else:
                print(f"处理{stock_code}的时候没有发现信号，继续处理下一个。")

        except Exception as e:
            print(f"处理股票代码 {stock_code} 时出现错误: {str(e)}，跳过该股票继续处理下一个。")
        finally:
            remaining_count = len(stock_code_list) - (count + 1)
            print(f"还剩下{remaining_count}个股票待分析")
            count = count + 1
            time.sleep(10) # 防止请求次数过高引发的接口异常

    # 输出结果
    print("循环结束")
    output_df = pd.DataFrame(result_list)
    print(output_df.head())
