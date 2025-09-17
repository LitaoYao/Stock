# -*- encoding=utf-8 -*-
import configparser
import datetime
import os
import requests
import sys
import time
import unicodedata

class StockMonitor:
	def __init__(self, config_file='config.ini'):
		self.config_file = config_file
		self.stock_codes = []
		self.refresh_interval = 5  # 默认5秒刷新
		self.load_config()

	def load_config(self):
		"""从配置文件加载股票代码和设置"""
		config = configparser.ConfigParser()

		# 如果配置文件不存在，创建默认配置
		if not os.path.exists(self.config_file):
			self.create_default_config()
			print(f"已创建默认配置文件 {self.config_file}，请编辑后重新运行程序")
			exit(0)

		config.read(self.config_file, encoding='utf-8')

		# 读取股票代码
		if 'Stocks' in config:
			self.stock_codes = [code.strip() for code in config['Stocks'].get('codes', '').split(',') if code.strip()]

		# 读取刷新间隔
		if 'Settings' in config:
			self.refresh_interval = config['Settings'].getint('refresh_interval', 5)

	def create_default_config(self):
		"""创建默认配置文件"""
		config = configparser.ConfigParser()

		config['Stocks'] = {
			'# 在此处添加A股代码，用逗号分隔': '',
			'# 沪市股票以sh前缀，深市股票以sz前缀': '',
			'codes': 'sh601318,sz000001,sh600036,sz000858'
		}

		config['Settings'] = {
			'# 刷新间隔(秒)': '',
			'refresh_interval': '5'
		}

		with open(self.config_file, 'w', encoding='utf-8') as f:
			config.write(f)

	def get_stock_price_optimized(self, stock_code):
		"""
		从腾讯API获取股票实时价格（优化版，只获取指定字段）
		返回字典包含: name, current, open, close, high, low
		"""
		try:
			# 使用一个更简洁的API接口（示例，实际需替换为腾讯可用且稳定的接口）
			url = f"http://qt.gtimg.cn/q={stock_code}"
			headers = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
			}

			# 设置较短的超时时间，避免长时间等待
			response = requests.get(url, headers=headers, timeout=5)
			response.encoding = 'gbk'  # 部分接口可能使用非UTF-8编码，如gbk

			if response.status_code == 200:
				# 示例返回数据格式（实际需根据接口响应调整解析逻辑）:
				# v_sh601318="1~中国平安~601318~27.85~27.80~27.82~278909~155197~~6717.72";
				# 数据字段可能以波浪线(~)分隔，依次可能是：未知、名称、代码、当前价、开盘、昨收、最高、最低、成交量(手)、成交额(万)...
				raw_data = response.text
				data_str = raw_data.split('="')[1].rstrip('";')
				fields = data_str.split('~')

				# 重要：以下字段索引需要根据实际API返回的数据顺序进行调整！
				# 这里是一个猜测的顺序，你必须根据实际情况校验和修改索引号
				stock_info = {
					'name': fields[1],            # 股票名称
					'current': float(fields[3]),  # 当前价格
					'close': float(fields[4]),    # 昨日收盘
					'open': float(fields[5]),     # 今日开盘
					'high': float(fields[33]),    # 最高
					'low': float(fields[34])      # 最低
				}
				return stock_info
			else:
				print(f"请求失败，状态码: {response.status_code}")
				return None
		except requests.exceptions.Timeout:
			print(f"获取 {stock_code} 数据超时，请检查网络或稍后重试")
			return None
		except requests.exceptions.RequestException as e:
			print(f"获取 {stock_code} 数据时发生网络错误: {e}")
			return None
		except (IndexError, ValueError, KeyError) as e:
			print(f"解析 {stock_code} 返回数据时发生错误: {e}。原始数据: {raw_data}")
			return None
		except Exception as e:
			print(f"获取 {stock_code} 数据时发生未知错误: {e}")
			return None

	def get_display_width(self, s):
		"""
		计算字符串的显示宽度（考虑中英文字符宽度差异）
		全角字符（如汉字）宽度为2，半角字符（如英文字母、数字）宽度为1
		"""
		width = 0
		for char in s:
			# 判断字符宽度：'F'（全角）、'W'（宽）、'Na'（窄）等类别
			if unicodedata.east_asian_width(char) in ('F', 'W'):
				width += 2
			else:
				width += 1
		return width

	# 创建一个辅助函数来对齐文本（考虑显示宽度）
	def align_text(self, text, target_width, align='left'):
		actual_width = self.get_display_width(str(text))
		padding_needed = target_width - actual_width
		if padding_needed <= 0:
			return str(text)
		if align == 'left':
			return str(text) + ' ' * padding_needed
		elif align == 'right':
			return ' ' * padding_needed + str(text)
		elif align == 'center':
			left_padding = padding_needed // 2
			right_padding = padding_needed - left_padding
			return ' ' * left_padding + str(text) + ' ' * right_padding
		else:
			return str(text)

	def display_one_line(self, str_dict):

		# 计算各字段所需的显示宽度（根据你的表格布局调整）
		code_width = 10    # 代码列宽
		name_width = 12    # 名称列宽
		price_width = 10   # 价格列宽
		change_width = 18  # 涨跌列宽（包含颜色符号可能占用的额外宽度）
		high_width = 10    # 最高列宽
		low_width = 10     # 最低列宽
		# 对齐每个字段
		aligned_code = self.align_text(str_dict['code'], code_width, 'left')
		aligned_name = self.align_text(str_dict['name'], name_width, 'left')
		aligned_price = self.align_text(str_dict['current'], price_width, 'right')
		aligned_change = self.align_text(str_dict['change'], change_width, 'right')
		aligned_high = self.align_text(str_dict['high'], high_width, 'right')
		aligned_low = self.align_text(str_dict['low'], low_width, 'right')
		# 打印对齐后的行
		print(f"{aligned_code} {aligned_name} {aligned_price} {aligned_change} {aligned_high} {aligned_low}")

	def display_stock_info(self, stock_info, stock_code):
		"""显示股票信息"""
		if stock_info:
			change = stock_info['current'] - stock_info['close']
			change_percent = (change / stock_info['close']) * 100
			# 确定颜色和涨跌符号（Unix终端适用）
			color_code = "\033[32m" if change < 0 else "\033[31m"
			reset_code = "\033[0m"
			symbol = "↑" if change >= 0 else "↓"
			# 准备要显示的字段
			name_display = stock_info['name']                # 股票名称
			code_display = stock_code                        # 股票代码
			price_display = f"{stock_info['current']:>.2f}"  # 当前价
			change_display = f"{change:>+7.2f}"              # 涨跌额
			percent_display = f"({change_percent:>+6.2f}%)"  # 涨跌幅
			high_display = f"{stock_info['high']:>7.2f}"     # 最高
			low_display = f"{stock_info['low']:>7.2f}"       # 最低
			# 涨跌额和涨跌幅通常一起显示，可能需要特殊处理颜色和符号
			change_str = f"{color_code}{change_display} {percent_display}{symbol}{reset_code}"
			str_dict = {
				'code': code_display,
				'name': name_display,
				'current': price_display,
				'change': change_str,
				'high': high_display,
				'low': low_display,
			}
			self.display_one_line(str_dict)
		else:
			# 处理数据为空的情况，也保持对齐
			print(f"{stock_code:>10} {'N/A':>12} {'N/A':>10} {'N/A':>18} {'N/A':>10} {'N/A':>10}")

	def run(self):
		"""主运行循环"""
		if not self.stock_codes:
			print("配置文件中未找到有效的股票代码")
			return
		try:
			print("\033[2J")
			while True:
				sys.stdout.write('\033[;H')
				sys.stdout.flush()
				str_dict = {
					'code': '代码',
					'name': '名称',
					'current': '当前',
					'change': '涨跌',
					'high': '最高',
					'low': '最低',
				}
				self.display_one_line(str_dict)
				stock_info_list = []
				for code in self.stock_codes:
					stock_info = self.get_stock_price_optimized(code)
					stock_info_list.append(stock_info)
				for stock_info in sorted(stock_info_list, key=lambda stock_info: (stock_info['current'] - stock_info['close']) / stock_info['close'], reverse=True):
					self.display_stock_info(stock_info, code)
				print('最后刷新时间: ', datetime.datetime.now())
				sys.stdout.flush()
				time.sleep(self.refresh_interval)
		except KeyboardInterrupt:
			print("\n程序已退出")

if __name__ == "__main__":
	monitor = StockMonitor()
	monitor.run()

